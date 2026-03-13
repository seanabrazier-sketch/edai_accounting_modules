"""
rates_db.py — 50-state rates database for the Fiscal Impact Engine.

Loads all extracted JSON rate tables from data/fiscal_impact/rates/ and
provides clean lookup functions with county → state → national fallback.

Usage:
    from fiscal_impact.rates_db import RatesDB
    db = RatesDB()
    rate = db.get_pit_effective_rate("Virginia", income=75_000)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Path resolution ────────────────────────────────────────────────────────────
# rates_db.py lives at src/fiscal_impact/rates_db.py
# data is at  <repo_root>/data/fiscal_impact/rates/
_REPO_ROOT  = Path(__file__).parent.parent.parent
_RATES_DIR  = _REPO_ROOT / "data" / "fiscal_impact" / "rates"

# ── BPOL constants (Richmond, VA only) ────────────────────────────────────────
# Business, Professional, and Occupational License tax
# Rate = dollars per $100 of gross receipts → divide by 100 for fraction
BPOL_RATES_RVA = {
    "professional":  0.0058 / 100,   # 0.0058% of gross receipts
    "contractors":   0.0019 / 100,
    "retail":        0.0020 / 100,
    "wholesale":     0.0022 / 100,
}
BPOL_LOCALITY = ("Virginia", "Richmond")

# ── State name aliases ─────────────────────────────────────────────────────────
_STATE_ALIASES = {
    "D.C.":                  "District of Columbia",
    "DC":                    "District of Columbia",
    "Washington D.C.":       "District of Columbia",
    "Washington, D.C.":      "District of Columbia",
    "Washington DC":         "District of Columbia",
}


def _normalize_state(raw: str) -> str:
    """Strip footnote letters e.g. 'California (b)' → 'California'; resolve aliases."""
    if not isinstance(raw, str):
        return raw
    s = raw.strip()
    # Check alias map first
    if s in _STATE_ALIASES:
        return _STATE_ALIASES[s]
    # Strip parenthetical footnotes like "(b)", "(c)"
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s).strip()
    if s in _STATE_ALIASES:
        return _STATE_ALIASES[s]
    return s


class RatesDB:
    """
    50-state rates database loaded from extracted JSON files.

    Provides lookup functions for all rate types needed by the Fiscal Impact
    Engine.  Fallback order: county → state → national average.
    """

    def __init__(self, rates_dir: Optional[Path] = None):
        self._dir = Path(rates_dir) if rates_dir else _RATES_DIR
        self._load_all()

    # ── Loader ─────────────────────────────────────────────────────────────────

    def _load_all(self):
        def _j(fname):
            with open(self._dir / fname) as f:
                return json.load(f)

        pit_raw       = _j("pit_rates.json")
        sales_raw     = _j("sales_tax_rates.json")
        cit_raw       = _j("cit_rates.json")
        prop_raw      = _j("property_tax_rates.json")
        rims_raw      = _j("rims2_multipliers.json")
        irs_raw       = _j("irs_ratios.json")
        util_raw      = _j("utility_assumptions.json")
        capex_raw     = _j("capex_splits.json")
        ces_raw       = _j("ces_spending.json")
        econ_raw      = _j("economic_rates.json")

        # ── PIT brackets: state → sorted list of (bracket_floor, rate, deduction, exemption)
        self._pit_brackets: Dict[str, List[dict]] = {}
        for row in pit_raw.get("bracket_rates", []):
            st = _normalize_state(row.get("state", ""))
            if not st:
                continue
            self._pit_brackets.setdefault(st, []).append(row)
        # Sort each state's brackets by floor amount
        for st in self._pit_brackets:
            self._pit_brackets[st].sort(key=lambda r: _to_float(r.get("Single Bracket", 0)) or 0)

        self._pit_va_calcs = pit_raw.get("richmond_va_calcs", {})

        # ── Sales tax: state → record
        self._sales_tax: Dict[str, dict] = {}
        for row in sales_raw.get("rates", []):
            raw_st = row.get("State") or row.get("state", "")
            st = _normalize_state(raw_st)
            if st:
                self._sales_tax[st] = row

        # ── CIT: state → flat/top rate (largest bracket's rate for that state)
        self._cit: Dict[str, float] = {}
        cit_by_state: Dict[str, List[dict]] = {}
        for row in cit_raw.get("cit_brackets", []):
            raw_st = row.get("State") or row.get("state", "")
            st = _normalize_state(raw_st)
            if st:
                cit_by_state.setdefault(st, []).append(row)
        for st, rows in cit_by_state.items():
            # CIT field name is 'Rates' (capital R, plural) in this dataset
            top = max(rows, key=lambda r: _to_float(r.get("Rates") or r.get("Rate") or r.get("rate") or 0) or 0)
            self._cit[st] = _to_float(top.get("Rates") or top.get("Rate") or top.get("rate")) or 0.0

        # ── GRT: state → rate
        # Field structure: 'SB gross receipts notes' = text (or 0), 'Rate to use' = decimal rate
        self._grt: Dict[str, float] = {}
        for row in cit_raw.get("grt_rates", []):
            raw_st = row.get("State") or row.get("state", "")
            st = _normalize_state(raw_st)
            if not st:
                continue
            rate_val = _to_float(row.get("Rate to use") or row.get("Rate") or row.get("rate"))
            if rate_val is not None and rate_val > 0:
                self._grt[st] = rate_val

        # ── Property tax: state → city records list + state-level averages
        self._prop_city: Dict[str, List[dict]] = {}
        for row in prop_raw.get("lincoln_city_data", []):
            st = _normalize_state(row.get("state", ""))
            if st:
                self._prop_city.setdefault(st, []).append(row)

        self._prop_state: Dict[str, dict] = {}
        for row in prop_raw.get("lincoln_state_data", []):
            raw_st = row.get("State") or row.get("state", "")
            st = _normalize_state(raw_st)
            if st:
                self._prop_state[st] = row

        # ── RIMS II: state → sector → multipliers
        # Policy: states other than VA and NC use Richmond VA multipliers as placeholder
        rva_sectors = {r["Cleaned sector"]: r for r in rims_raw.get("richmond_va", []) if r.get("Cleaned sector")}
        gnc_sectors = {r["Cleaned sector"]: r for r in rims_raw.get("greenville_nc", []) if r.get("Cleaned sector")}
        self._rims2_rva = rva_sectors
        self._rims2_gnc = gnc_sectors

        # ── IRS sector ratios: sector_name → record
        self._irs_sectors: Dict[str, dict] = {}
        for row in irs_raw.get("irs_summary", []):
            key = str(row.get("2013 sector to use", "")).strip()
            if key:
                self._irs_sectors[key] = row

        # Pre-compute national average payroll-to-receipts ratio from "All industries total"
        all_ind = self._irs_sectors.get("All industries total", {})
        sal = _to_float(all_ind.get("Salaries and wages_sum")) or 1.0
        rec = _to_float(all_ind.get("Total receipts_sum")) or 1.0
        self._national_payroll_to_receipts = sal / rec   # ~0.XX (payroll / receipts)

        # ── Utility assumptions: key → value
        self._util_kv: Dict[str, float] = util_raw.get("assumptions_kv", {})
        self._util_key_values: Dict[str, float] = util_raw.get("key_values", {})
        self._energy_by_bldg: List[dict] = util_raw.get("energy_by_building_type", [])

        # ── Capex splits: category → {generic_share, commercial_share}
        self._capex_splits: Dict[str, dict] = {}
        for row in capex_raw.get("capex_splits", []):
            cat = row.get("category", "")
            if cat:
                self._capex_splits[cat.lower()] = row

        # ── CES spending
        self._ces_categories = ces_raw.get("ces_categories", [])
        self._ces_taxed_spend = ces_raw.get("ces_taxed_spend", [])
        self._taxable_spend_share = ces_raw.get("taxable_spend_share", 0.3765)

        # ── Economic rates: metric → value
        self._econ_rates: Dict[str, float] = {}
        for row in econ_raw.get("economic_rates", []):
            key = str(row.get("metric", "")).strip().lower()
            val = _to_float(row.get("value"))
            if key and val is not None:
                self._econ_rates[key] = val

        # Also hardcode the key rates from the key_rates dict if present
        for k, v in econ_raw.get("key_rates", {}).items():
            self._econ_rates[k] = v

        # ── BLS state wages: state → avg_annual_wage
        self._bls_wages: Dict[str, float] = {}
        for row in econ_raw.get("bls_state_wages", []):
            raw_st = row.get("State") or row.get("state", "")
            st = _normalize_state(raw_st)
            if not st:
                continue
            # Try various annual wage field names
            wage = None
            for field in ("Annual wages (52 weeks)", "Annual mean wage", "Avg Annual Pay",
                          "avg_annual_pay", "Mean Annual Wage", "Total", "2021", "2020", "2019"):
                v = row.get(field)
                if v is not None:
                    wage = _to_float(v)
                    if wage and wage > 1000:  # sanity: should be > $1,000
                        break
            if wage and st:
                self._bls_wages[st] = wage

        # National BLS average fallback
        if self._bls_wages:
            self._national_avg_wage = sum(self._bls_wages.values()) / len(self._bls_wages)
        else:
            self._national_avg_wage = 58_000.0  # approximate US average

    # ── PIT ────────────────────────────────────────────────────────────────────

    def get_pit_effective_rate(
        self,
        state: str,
        income: float,
        filing_status: str = "single",
    ) -> float:
        """
        Effective (not marginal) PIT rate for the given state and annual income.

        Returns effective rate = tax_liability / gross_income.
        Handles progressive brackets, standard deduction, and personal exemption.
        States with no income tax return 0.0.
        """
        st = _normalize_state(state)
        brackets = self._pit_brackets.get(st, [])
        if not brackets:
            return 0.0  # no-income-tax state

        is_married = filing_status.lower() in ("married", "joint", "mfj")
        rate_field    = "Married rate"    if is_married else "Single Rate"
        bracket_field = "Married bracket" if is_married else "Single Bracket"
        deduction_field = "Married Std Deduction" if is_married else "Single Std Deduction"
        exemption_field = "Couple Pers Exempt"    if is_married else "Single Pers Exempt"

        # Deduction + exemption from first bracket row (repeated across all rows)
        first = brackets[0]
        deduction = _to_float(first.get(deduction_field)) or 0.0
        exemption = _to_float(first.get(exemption_field)) or 0.0

        taxable = max(0.0, income - deduction - exemption)
        if taxable == 0:
            return 0.0

        # Build bracket table: [(floor, rate), ...]
        bkt_table: List[Tuple[float, float]] = []
        for row in brackets:
            floor = _to_float(row.get(bracket_field)) or 0.0
            rate  = _to_float(row.get(rate_field))    or 0.0
            bkt_table.append((floor, rate))
        bkt_table.sort(key=lambda x: x[0])

        # Compute progressive tax
        tax = 0.0
        for i, (floor, rate) in enumerate(bkt_table):
            if taxable <= floor:
                break
            next_floor = bkt_table[i + 1][0] if i + 1 < len(bkt_table) else float("inf")
            slice_top  = min(taxable, next_floor)
            tax += (slice_top - floor) * rate

        return tax / income  # effective rate over gross income

    def get_pit_marginal_rate(self, state: str, income: float, filing_status: str = "single") -> float:
        """Top marginal PIT rate that applies at the given income level."""
        st = _normalize_state(state)
        brackets = self._pit_brackets.get(st, [])
        if not brackets:
            return 0.0
        is_married = filing_status.lower() in ("married", "joint", "mfj")
        rate_field    = "Married rate"    if is_married else "Single Rate"
        bracket_field = "Married bracket" if is_married else "Single Bracket"
        deduction = _to_float(brackets[0].get("Married Std Deduction" if is_married else "Single Std Deduction")) or 0.0
        exemption = _to_float(brackets[0].get("Couple Pers Exempt" if is_married else "Single Pers Exempt")) or 0.0
        taxable = max(0.0, income - deduction - exemption)
        rate = 0.0
        for row in brackets:
            floor = _to_float(row.get(bracket_field)) or 0.0
            if taxable >= floor:
                rate = _to_float(row.get(rate_field)) or 0.0
        return rate

    # ── Sales Tax ──────────────────────────────────────────────────────────────

    def get_sales_tax_rate(self, state: str, county: str = None, rate_type: str = "combined") -> float:
        """
        Combined state+local sales tax rate for the given state.

        rate_type: 'combined' (default) | 'state_only' | 'local_only'
        county is accepted for future county-level lookups (not yet supported);
        falls back to state average.
        """
        st = _normalize_state(state)
        row = self._sales_tax.get(st)
        if row is None:
            # Try partial match
            for key in self._sales_tax:
                if key.lower().startswith(st.lower()):
                    row = self._sales_tax[key]
                    break
        if row is None:
            # National average fallback
            rates = [_to_float(r.get("Combined S&L Rate")) for r in self._sales_tax.values()]
            rates = [r for r in rates if r is not None]
            return sum(rates) / len(rates) if rates else 0.07

        if rate_type == "state_only":
            return _to_float(row.get("State Tax Rate")) or 0.0
        elif rate_type == "local_only":
            return _to_float(row.get("Avg. Local Tax Rate")) or 0.0
        else:  # combined
            v = _to_float(row.get("Combined S&L Rate"))
            if v is not None:
                return v
            return (_to_float(row.get("State Tax Rate")) or 0.0) + (_to_float(row.get("Avg. Local Tax Rate")) or 0.0)

    # ── CIT ────────────────────────────────────────────────────────────────────

    def get_cit_rate(self, state: str) -> float:
        """Top marginal corporate income tax rate for the given state. 0.0 if no CIT."""
        st = _normalize_state(state)
        return self._cit.get(st, 0.0)

    def get_grt_rate(self, state: str) -> float:
        """Gross receipts tax rate for the given state. 0.0 if state has no GRT."""
        st = _normalize_state(state)
        return self._grt.get(st, 0.0)

    # ── Property Tax ───────────────────────────────────────────────────────────

    def get_property_tax_rate(
        self,
        state: str,
        city: str = None,
        valuation: str = "1m",
    ) -> float:
        """
        Effective commercial property tax rate for the given state/city.

        valuation: '100k' or '1m' (default '1m') — Lincoln Institute valuation tier.
        Fallback: state-level average from Lincoln state cache.
        """
        st = _normalize_state(state)
        rate_field = "commercial_rate_100k" if valuation == "100k" else "commercial_rate_1m"

        # City-level lookup
        if city:
            city_rows = self._prop_city.get(st, [])
            for row in city_rows:
                if city.lower() in (row.get("city") or "").lower():
                    r = _to_float(row.get(rate_field))
                    if r is not None:
                        return r

        # State largest-city fallback (first entry per state = largest city)
        city_rows = self._prop_city.get(st, [])
        if city_rows:
            r = _to_float(city_rows[0].get(rate_field))
            if r is not None:
                return r

        # State-level average fallback
        state_row = self._prop_state.get(st, {})
        for field in ("Effective Tax Rate on Commercial Property",
                      "Commercial Effective Rate", "Eff Tax Rate 1M",
                      "commercial_rate_1m", "rate"):
            v = _to_float(state_row.get(field))
            if v is not None:
                return v

        # National average fallback
        rates = []
        for rows in self._prop_city.values():
            for row in rows:
                v = _to_float(row.get(rate_field))
                if v is not None:
                    rates.append(v)
        return sum(rates) / len(rates) if rates else 0.012  # ~1.2% national avg

    # ── RIMS II Multipliers ────────────────────────────────────────────────────

    def get_rims2_multipliers(self, state: str, sector: str = None) -> dict:
        """
        RIMS II Type II multipliers for the given state and sector.

        State policy: Virginia and NC → state-specific data.
        All other states → Richmond VA as placeholder (Session G policy).

        Returns dict with keys:
            output_mult, earnings_mult, employment_mult, value_added_mult,
            direct_earnings_mult, direct_employment_mult
        """
        st = _normalize_state(state)
        sectors = self._rims2_gnc if st in ("North Carolina",) else self._rims2_rva

        # Sector lookup with fallback
        row = None
        if sector:
            # Exact match
            row = sectors.get(sector)
            if row is None:
                # Partial match (case-insensitive)
                sector_lower = sector.lower()
                for key, val in sectors.items():
                    if sector_lower in key.lower() or key.lower() in sector_lower:
                        row = val
                        break

        if row is None:
            # Default: management/professional services sector
            for default_sector in (
                "Management of companies and enterprises",
                "Legal, accounting, and other professional services",
                "Professional and technical services",
                "Offices of other holding companies",
                "Administrative and support services",
            ):
                row = sectors.get(default_sector)
                if row is not None:
                    break

        if row is None:
            # Last resort: first non-zero-multiplier sector
            for r in sectors.values():
                if _to_float(r.get("Final-demand Employment /3/ (number of jobs)")) or 0 > 0:
                    row = r
                    break

        if row is None:
            return {
                "output_mult": 1.5, "earnings_mult": 0.6,
                "employment_mult": 12.0, "value_added_mult": 0.9,
                "direct_earnings_mult": 1.0, "direct_employment_mult": 1.0,
                "sector": "fallback",
            }

        return {
            "output_mult":            _to_float(row.get("Final-demand Output /1/ (dollars)"))     or 1.0,
            "earnings_mult":          _to_float(row.get("Final-demand Earnings /2/ (dollars)"))   or 0.5,
            "employment_mult":        _to_float(row.get("Final-demand Employment /3/ (number of jobs)")) or 10.0,
            "value_added_mult":       _to_float(row.get("Final-demand Value-added /4/ (dollars)")) or 0.8,
            "direct_earnings_mult":   _to_float(row.get("Direct-effect Earnings /5/ (dollars)"))  or 1.0,
            "direct_employment_mult": _to_float(row.get("Direct-effect Employment /6/ (number of jobs)")) or 1.0,
            "sector": row.get("Cleaned sector") or row.get("Sector", "unknown"),
        }

    def list_rims2_sectors(self, state: str = "Virginia") -> List[str]:
        """List all available RIMS II sector names for a state."""
        st = _normalize_state(state)
        sectors = self._rims2_gnc if st in ("North Carolina",) else self._rims2_rva
        return sorted(sectors.keys())

    # ── IRS Payroll-to-Receipts ────────────────────────────────────────────────

    def get_payroll_to_receipts_ratio(self, sector: str = None) -> float:
        """
        Ratio of payroll to gross receipts for the given NAICS sector.
        Used to estimate gross receipts from known payroll:
            gross_receipts = payroll / payroll_to_receipts_ratio

        Falls back to national average if sector not found.
        """
        if sector:
            row = self._irs_sectors.get(sector)
            if row is None:
                sector_lower = sector.lower()
                for key, val in self._irs_sectors.items():
                    if sector_lower in key.lower():
                        row = val
                        break
            if row is not None:
                sal = _to_float(row.get("Salaries and wages_sum")) or 0.0
                rec = _to_float(row.get("Total receipts_sum")) or 0.0
                if sal > 0 and rec > 0:
                    return sal / rec

        return self._national_payroll_to_receipts  # ~0.18 for all industries

    def get_receipts_to_payroll_multiplier(self, sector: str = None) -> float:
        """Inverse of payroll_to_receipts: gross_receipts = payroll * this_value."""
        ratio = self.get_payroll_to_receipts_ratio(sector)
        return 1.0 / ratio if ratio > 0 else 5.5  # ~5.5x national avg

    # ── BLS Wages ──────────────────────────────────────────────────────────────

    def get_bls_wage(self, state: str) -> float:
        """
        Average annual wage (BLS QCEW) for the given state.
        Used for indirect/induced worker wages in RIMS II multiplier calculations.
        Falls back to national average.
        """
        st = _normalize_state(state)
        wage = self._bls_wages.get(st)
        if wage is not None:
            return wage
        # Partial match
        for key, val in self._bls_wages.items():
            if key.lower().startswith(st.lower()):
                return val
        return self._national_avg_wage

    # ── Economic Rates ────────────────────────────────────────────────────────

    def get_economic_rate(self, key: str) -> float:
        """
        Retrieve economic rate constants.

        Common keys:
            'eci_inflation'              — Employment Cost Index (wage inflation)
            'cpi_inflation'              — Consumer Price Index
            'ppi_inflation'              — Producer Price Index
            'cre_inflation'              — Commercial Real Estate inflation
            'bartik_societal_discount'   — Societal discount rate (3%)
            'bartik_corporate_discount'  — Corporate discount rate (12%)
            'employment cost index'      — same as eci_inflation (raw key)
        """
        key_lower = key.lower()
        # Direct lookup
        if key_lower in self._econ_rates:
            return self._econ_rates[key_lower]
        # Partial match
        for k, v in self._econ_rates.items():
            if key_lower in k or k in key_lower:
                return v
        # Hardcoded fallbacks
        _defaults = {
            "eci":      0.032,
            "cpi":      0.0273,
            "ppi":      0.0232,
            "cre":      0.044,
            "societal": 0.03,
            "corporate":0.12,
            "discount": 0.03,
        }
        for fragment, val in _defaults.items():
            if fragment in key_lower:
                return val
        raise KeyError(f"Economic rate '{key}' not found in database.")

    def get_discount_rate(self, rate_type: str = "societal") -> float:
        """Convenience: get Bartik discount rate. rate_type='societal'|'corporate'"""
        if rate_type == "corporate":
            return self.get_economic_rate("bartik_corporate_discount")
        return self.get_economic_rate("bartik_societal_discount")

    def get_inflation_rate(self, inflation_type: str = "eci") -> float:
        """Convenience: get inflation rate. inflation_type='eci'|'cpi'|'ppi'|'cre'"""
        return self.get_economic_rate(inflation_type)

    # ── Utility Assumptions ───────────────────────────────────────────────────

    def get_utility_assumption(self, key: str, default=None):
        """
        Look up a utility assumption by key substring.

        Example keys:
            'Building size per worker'
            'Electricity consumption per sq. ft.'
            'Natural gas consumption per sq. ft.'
            'Taxes, electricity, annually, City of Richmond VA, Year 1'
        """
        # Check hardcoded key_values first
        for k, v in self._util_key_values.items():
            if key.lower() in k.lower() or k.lower() in key.lower():
                return v
        # Then full kv store
        for k, v in self._util_kv.items():
            if key.lower() in k.lower():
                return v
        return default

    def get_building_sqft_per_worker(self) -> float:
        """300 sq ft per worker (commercial office standard)."""
        return self._util_key_values.get("building_sq_ft_per_worker", 300.0)

    def get_electricity_intensity(self, building_type: str = "commercial") -> float:
        """kWh per sq ft per year for the given building type."""
        if building_type.lower() in ("commercial", "office"):
            return self._util_key_values.get("commercial_electricity_kwh_per_sqft_year", 13.63)
        # Look up in energy by building type table
        for row in self._energy_by_bldg:
            btype = str(row.get("col_0") or row.get("Building type") or "")
            if building_type.lower() in btype.lower():
                for col in ("Electricity (kWh/sq ft)", "electricity_kwh_sqft", "col_2"):
                    v = _to_float(row.get(col))
                    if v is not None:
                        return v
        return 13.63  # commercial default

    def get_gas_intensity(self, building_type: str = "commercial") -> float:
        """Natural gas cubic feet per sq ft per year."""
        if building_type.lower() in ("commercial", "office"):
            return self._util_key_values.get("commercial_gas_cuft_per_sqft_year", 14.57)
        return 14.57

    def get_richmond_utility_taxes(self) -> Tuple[float, float]:
        """
        Richmond VA Year 1 utility taxes (electricity, gas) in dollars.
        Returns (electricity_tax, gas_tax) for a ~250-worker, 40,000 sq ft facility.
        Scale proportionally by building size for other projects.
        """
        elec = self._util_key_values.get("richmond_electricity_tax_year1", 1322.16)
        gas  = self._util_key_values.get("richmond_gas_tax_year1", 446.24)
        return elec, gas

    # ── Capex Splits ──────────────────────────────────────────────────────────

    def get_capex_split(self, category: str, project_type: str = "commercial") -> float:
        """
        Fraction of total capex for the given category and project type.

        category:    'land' | 'construction material' | 'construction labor' |
                     'machinery and tools' | 'tangible personal property' | 'inventory'
        project_type:'commercial' | 'generic' | 'industrial'
        Returns decimal share (e.g., 0.167 for 16.7%).
        """
        cat_lower = category.lower()
        # Find matching row (partial match)
        row = None
        for key, r in self._capex_splits.items():
            if cat_lower in key or key in cat_lower:
                row = r
                break
        if row is None:
            return 0.0

        if project_type.lower() in ("commercial",):
            return row.get("commercial_share") or row.get("generic_share") or 0.0
        else:
            return row.get("generic_share") or 0.0

    def get_all_capex_splits(self, project_type: str = "commercial") -> Dict[str, float]:
        """Returns all capex splits as {category: share} dict for the given project type."""
        result = {}
        for key, row in self._capex_splits.items():
            if project_type.lower() == "commercial":
                # For commercial: use commercial_share if present (even if 0.0); do NOT fall back to generic
                v = row.get("commercial_share")
                if v is None:
                    v = 0.0
            else:
                v = row.get("generic_share") or 0.0
            result[row.get("category", key)] = v
        return result

    # ── BPOL ─────────────────────────────────────────────────────────────────

    def get_bpol_rate(
        self,
        state: str,
        locality: str = None,
        occupation_type: str = "professional",
    ) -> float:
        """
        BPOL (Business, Professional, and Occupational License) tax rate.

        Only Richmond, VA has BPOL.  All other state/locality combinations
        return 0.0 by design.

        occupation_type: 'professional' | 'contractors' | 'retail' | 'wholesale'
        Returns rate as fraction of gross receipts (e.g., 0.000058 for $0.0058/$100).
        """
        st = _normalize_state(state)
        if st != BPOL_LOCALITY[0]:
            return 0.0
        if locality and "richmond" not in locality.lower():
            return 0.0
        # Richmond, VA
        occ = occupation_type.lower()
        return BPOL_RATES_RVA.get(occ, BPOL_RATES_RVA["professional"])

    # ── CES Spending ──────────────────────────────────────────────────────────

    def get_taxable_spend_share(self) -> float:
        """
        Share of income spent on taxable goods/services (for sales tax base calc).
        37.65% per session brief (hardcoded, derived from BLS CES).
        """
        return self._taxable_spend_share

    # ── Convenience: full LocationRates dict ─────────────────────────────────

    def get_location_rates(
        self,
        state: str,
        county: str = None,
        city: str = None,
        project_type: str = "commercial",
        rims2_sector: str = None,
        irs_sector: str = None,
        average_salary: float = 75_000.0,
        filing_status: str = "single",
    ) -> dict:
        """
        Returns a complete dict of all rates for a given location,
        ready to be consumed by models.LocationRates.

        This is the primary entry point for the fiscal engine.
        """
        return {
            # PIT
            "pit_effective_rate":         self.get_pit_effective_rate(state, average_salary, filing_status),
            "pit_marginal_rate":          self.get_pit_marginal_rate(state, average_salary, filing_status),
            # Sales tax
            "sales_tax_rate":             self.get_sales_tax_rate(state, county),
            "sales_tax_state_only":       self.get_sales_tax_rate(state, county, "state_only"),
            "sales_tax_local_only":       self.get_sales_tax_rate(state, county, "local_only"),
            # Business taxes
            "cit_rate":                   self.get_cit_rate(state),
            "grt_rate":                   self.get_grt_rate(state),
            "bpol_rate_professional":     self.get_bpol_rate(state, city, "professional"),
            "bpol_rate_retail":           self.get_bpol_rate(state, city, "retail"),
            # Property tax
            "property_tax_rate":          self.get_property_tax_rate(state, city, "1m"),
            # RIMS II
            "rims2":                      self.get_rims2_multipliers(state, rims2_sector),
            # Wages
            "state_avg_annual_wage":      self.get_bls_wage(state),
            # Payroll-to-receipts
            "payroll_to_receipts_ratio":  self.get_payroll_to_receipts_ratio(irs_sector),
            "receipts_to_payroll_mult":   self.get_receipts_to_payroll_multiplier(irs_sector),
            # Economic rates
            "eci_inflation":              self.get_inflation_rate("eci"),
            "cpi_inflation":              self.get_inflation_rate("cpi"),
            "ppi_inflation":              self.get_inflation_rate("ppi"),
            "cre_inflation":              self.get_inflation_rate("cre"),
            "societal_discount_rate":     self.get_discount_rate("societal"),
            "corporate_discount_rate":    self.get_discount_rate("corporate"),
            # Utility assumptions
            "building_sqft_per_worker":   self.get_building_sqft_per_worker(),
            "electricity_kwh_per_sqft":   self.get_electricity_intensity("commercial"),
            "gas_cuft_per_sqft":          self.get_gas_intensity("commercial"),
            # Consumer spending
            "taxable_spend_share":        self.get_taxable_spend_share(),
            # Capex splits
            "capex_splits":               self.get_all_capex_splits(project_type),
        }

    # ── Diagnostics ────────────────────────────────────────────────────────────

    def coverage_report(self) -> str:
        lines = [
            "RatesDB Coverage Report",
            "=" * 60,
            f"  PIT states:          {len(self._pit_brackets)} states",
            f"  Sales tax states:    {len(self._sales_tax)} states",
            f"  CIT states:          {len(self._cit)} states",
            f"  GRT states:          {len(self._grt)} states",
            f"  Property tax states: {len(self._prop_city)} states (city), {len(self._prop_state)} (state avg)",
            f"  RIMS II sectors:     {len(self._rims2_rva)} (RVA), {len(self._rims2_gnc)} (Greenville NC)",
            f"  IRS sectors:         {len(self._irs_sectors)} sectors",
            f"  BLS wage states:     {len(self._bls_wages)} states",
            f"  Economic rates:      {len(self._econ_rates)} metrics",
            f"  Utility KV pairs:    {len(self._util_kv)} pairs",
            f"  Capex categories:    {len(self._capex_splits)} categories",
            f"  National avg wage:   ${self._national_avg_wage:,.0f}",
            f"  National P/R ratio:  {self._national_payroll_to_receipts:.4f}",
        ]
        return "\n".join(lines)


# ── Module-level singleton ────────────────────────────────────────────────────

_db: Optional[RatesDB] = None


def get_db() -> RatesDB:
    """Return module-level singleton RatesDB (lazy-loaded)."""
    global _db
    if _db is None:
        _db = RatesDB()
    return _db


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_float(v) -> Optional[float]:
    """Safely convert a value to float; returns None on failure."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace('%', '').replace(',', '').replace('$', '').strip("'")
        try:
            return float(s)
        except ValueError:
            return None
    return None


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("Loading RatesDB...")
    db = RatesDB()
    print(db.coverage_report())
    print()

    # ── Spot checks ────────────────────────────────────────────────────────────
    errors = []

    def check(label, got, expected_range_or_value, tol=0.05):
        if isinstance(expected_range_or_value, tuple):
            lo, hi = expected_range_or_value
            ok = lo <= got <= hi
        else:
            ok = abs(got - expected_range_or_value) / (abs(expected_range_or_value) + 1e-9) < tol
        status = "✅" if ok else "❌"
        print(f"  {status} {label}: {got}")
        if not ok:
            errors.append(f"{label}: got {got}, expected {expected_range_or_value}")

    print("── PIT ──────────────────────────────────────────────────────────────")
    check("Virginia PIT @ $75K (effective)",
          db.get_pit_effective_rate("Virginia", 75_000),
          (0.04, 0.055))
    check("Virginia PIT @ $75K (marginal)",
          db.get_pit_marginal_rate("Virginia", 75_000),
          (0.055, 0.06))
    check("Texas PIT @ $75K (no income tax)",
          db.get_pit_effective_rate("Texas", 75_000),
          0.0, tol=0.001)
    check("Florida PIT (no income tax)",
          db.get_pit_effective_rate("Florida", 100_000),
          0.0, tol=0.001)

    print("\n── Sales Tax ─────────────────────────────────────────────────────────")
    check("Virginia combined sales tax",
          db.get_sales_tax_rate("Virginia"),
          (0.055, 0.065))
    check("Oregon (no sales tax)",
          db.get_sales_tax_rate("Oregon"),
          (0.0, 0.005))

    print("\n── CIT ───────────────────────────────────────────────────────────────")
    check("Virginia CIT",
          db.get_cit_rate("Virginia"),
          (0.05, 0.065))

    print("\n── GRT ───────────────────────────────────────────────────────────────")
    grt_va = db.get_grt_rate("Virginia")
    print(f"  Virginia GRT: {grt_va} (expected 0.0 — VA has no GRT)")

    print("\n── Property Tax ─────────────────────────────────────────────────────")
    check("Virginia property tax rate (city $1M)",
          db.get_property_tax_rate("Virginia"),
          (0.005, 0.015))
    check("Texas property tax (should be >1%)",
          db.get_property_tax_rate("Texas"),
          (0.01, 0.025))

    print("\n── RIMS II ───────────────────────────────────────────────────────────")
    r = db.get_rims2_multipliers("Virginia", "Management of companies")
    print(f"  VA RIMS2 management: employ_mult={r['employment_mult']:.4f}, sector='{r['sector']}'")
    check("Employment multiplier > 1",
          r["employment_mult"],
          (1.0, 100.0))

    print("\n── BLS Wages ─────────────────────────────────────────────────────────")
    va_wage = db.get_bls_wage("Virginia")
    print(f"  Virginia avg annual wage: ${va_wage:,.0f}")
    check("Virginia wage reasonable",
          va_wage,
          (30_000, 120_000))

    print("\n── Economic Rates ────────────────────────────────────────────────────")
    check("ECI inflation",   db.get_inflation_rate("eci"),   0.032, tol=0.05)
    check("CPI inflation",   db.get_inflation_rate("cpi"),   0.0273, tol=0.05)
    check("Societal discount", db.get_discount_rate("societal"), 0.03, tol=0.01)
    check("Corporate discount",db.get_discount_rate("corporate"), 0.12, tol=0.01)

    print("\n── BPOL ──────────────────────────────────────────────────────────────")
    check("Richmond BPOL professional",
          db.get_bpol_rate("Virginia", "Richmond", "professional"),
          0.000058, tol=0.01)
    check("Non-Richmond BPOL = 0",
          db.get_bpol_rate("Texas", "Austin"),
          0.0, tol=0.001)

    print("\n── Payroll/Receipts ──────────────────────────────────────────────────")
    p2r = db.get_payroll_to_receipts_ratio()
    print(f"  National P/R ratio: {p2r:.4f}  → receipts mult: {1/p2r:.2f}x payroll")

    print("\n── Location Rates Bundle ─────────────────────────────────────────────")
    loc = db.get_location_rates("Virginia", city="Richmond", average_salary=75_000)
    print(f"  PIT effective: {loc['pit_effective_rate']:.4f}")
    print(f"  Sales tax:     {loc['sales_tax_rate']:.4f}")
    print(f"  Property tax:  {loc['property_tax_rate']:.4f}")
    print(f"  CIT:           {loc['cit_rate']:.4f}")
    print(f"  BPOL prof:     {loc['bpol_rate_professional']:.6f}")

    print()
    if errors:
        print(f"❌ {len(errors)} FAILURES:")
        for e in errors:
            print(f"   {e}")
        sys.exit(1)
    else:
        print("✅ All spot checks passed.")
