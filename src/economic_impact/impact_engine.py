"""
Economic Impact calculation engine.

Implements a two-phase calculation:
  Phase 1 — Operations:    Ongoing annual economic impact of direct jobs.
  Phase 2 — Construction:  One-time economic impact of capital expenditure.

Called exclusively by impact_model.py; does not load data files directly.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    ConstructionImpact,
    EconomicImpactResult,
    OperationsImpact,
    ProjectEconomicInputs,
    RIMSMultiplierSet,
    SectorBreakdownRow,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "economic_impact"

# ─────────────────────────────────────────────────────────────────────────────
# BEA aggregate-sector → NAICS 2-digit code
# Used to find SUSB payroll-to-sales ratios
# ─────────────────────────────────────────────────────────────────────────────
_BEA_TO_NAICS2: Dict[str, str] = {
    "agriculture, forestry, fishing and hunting":   "11.0",
    "mining, quarrying, and oil and gas extraction":"21.0",
    "utilities":                                    "22.0",
    "construction":                                 "23.0",
    "durable goods manufacturing":                  "31-33",
    "nondurable goods manufacturing":               "31-33",
    "wholesale trade":                              "42.0",
    "retail trade":                                 "44-45",
    "transportation and warehousing":               "48-49",
    "information":                                  "51.0",
    "finance and insurance":                        "52.0",
    "real estate and rental and leasing":           "53.0",
    "professional, scientific, and technical services": "54.0",
    "management of companies and enterprises":      "55.0",
    "administrative and support and waste management and remediation services": "56.0",
    "educational services":                         "61.0",
    "health care and social assistance":            "62.0",
    "arts, entertainment, and recreation":          "71.0",
    "accommodation":                                "72.0",
    "food services and drinking places":            "72.0",
    "other services":                               "81.0",
}

# ─────────────────────────────────────────────────────────────────────────────
# BEA 64-industry → aggregate sector (used for sector breakdown lookup)
# Maps each detailed industry's sector_code in TotMult → aggregate sector name
# ─────────────────────────────────────────────────────────────────────────────
_INDUSTRY_TO_AGG_SECTOR: Dict[str, str] = {
    "1.0":  "Agriculture, forestry, fishing and hunting",
    "2.0":  "Agriculture, forestry, fishing and hunting",
    "3.0":  "Mining, quarrying, and oil and gas extraction",
    "4.0":  "Mining, quarrying, and oil and gas extraction",
    "5.0":  "Mining, quarrying, and oil and gas extraction",
    "6.0":  "Utilities*",
    "7.0":  "Construction",
    "8.0":  "Durable goods manufacturing",
    "9.0":  "Durable goods manufacturing",
    "10.0": "Durable goods manufacturing",
    "11.0": "Durable goods manufacturing",
    "12.0": "Durable goods manufacturing",
    "13.0": "Durable goods manufacturing",
    "14.0": "Durable goods manufacturing",
    "15.0": "Durable goods manufacturing",
    "16.0": "Durable goods manufacturing",
    "17.0": "Durable goods manufacturing",
    "18.0": "Durable goods manufacturing",
    "19.0": "Nondurable goods manufacturing",
    "20.0": "Nondurable goods manufacturing",
    "21.0": "Nondurable goods manufacturing",
    "22.0": "Nondurable goods manufacturing",
    "23.0": "Nondurable goods manufacturing",
    "24.0": "Nondurable goods manufacturing",
    "25.0": "Nondurable goods manufacturing",
    "26.0": "Nondurable goods manufacturing",
    "27.0": "Wholesale trade",
    "28.0": "Retail trade",
    "29.0": "Retail trade",
    "30.0": "Retail trade",
    "31.0": "Retail trade",
    "32.0": "Transportation and warehousing*",
    "33.0": "Transportation and warehousing*",
    "34.0": "Transportation and warehousing*",
    "35.0": "Transportation and warehousing*",
    "36.0": "Transportation and warehousing*",
    "37.0": "Transportation and warehousing*",
    "38.0": "Transportation and warehousing*",
    "39.0": "Transportation and warehousing*",
    "40.0": "Information",
    "41.0": "Information",
    "42.0": "Information",
    "43.0": "Information",
    "44.0": "Finance and insurance",
    "45.0": "Finance and insurance",
    "46.0": "Finance and insurance",
    "47.0": "Finance and insurance",
    "48.0": "Real estate and rental and leasing",
    "49.0": "Real estate and rental and leasing",
    "50.0": "Professional, scientific, and technical services",
    "51.0": "Management of companies and enterprises",
    "52.0": "Administrative and support and waste management and remediation services",
    "53.0": "Administrative and support and waste management and remediation services",
    "54.0": "Educational services",
    "55.0": "Health care and social assistance",
    "56.0": "Health care and social assistance",
    "57.0": "Health care and social assistance",
    "58.0": "Health care and social assistance",
    "59.0": "Arts, entertainment, and recreation",
    "60.0": "Arts, entertainment, and recreation",
    "61.0": "Accommodation",
    "62.0": "Food services and drinking places",
    "63.0": "Other services*",
    "64.0": "Households",
}


# ─────────────────────────────────────────────────────────────────────────────
# Lazy-loaded data
# ─────────────────────────────────────────────────────────────────────────────
_crosswalk: Optional[List[Dict]] = None
_susb: Optional[Dict]            = None


def _load_crosswalk() -> List[Dict]:
    global _crosswalk
    if _crosswalk is None:
        with open(_DATA_DIR / "sector_crosswalk.json") as f:
            _crosswalk = json.load(f)
    return _crosswalk


def _load_susb() -> Dict:
    global _susb
    if _susb is None:
        with open(_DATA_DIR / "susb_national.json") as f:
            _susb = json.load(f)
    return _susb


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Sector mapping
# ─────────────────────────────────────────────────────────────────────────────

def _map_sector(user_sector: str) -> Optional[str]:
    """Map user sector label → BEA industry name via sector_crosswalk.json.

    Matching is case-insensitive and strips whitespace.  Returns the first
    bea_industry value found, or None if no match.
    """
    crosswalk = _load_crosswalk()
    needle = user_sector.strip().lower()
    for entry in crosswalk:
        if entry["irs_sector"].strip().lower() == needle:
            return entry["bea_industry"]
    # Partial / fuzzy fallback — match any crosswalk entry whose irs_sector
    # contains the user's sector as a substring.
    for entry in crosswalk:
        if needle in entry["irs_sector"].strip().lower():
            bea = entry["bea_industry"]
            logger.debug(
                "Fuzzy sector match: '%s' → '%s' (via '%s')",
                user_sector, bea, entry["irs_sector"],
            )
            return bea
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Lookup BEA industry code and TotMult row
# ─────────────────────────────────────────────────────────────────────────────

def _find_totmult_row(bea_industry_name: str, mult_set: RIMSMultiplierSet) -> Optional[Dict]:
    """Return the TotMult row dict matching the given BEA industry name."""
    totmult_rows = mult_set.tables["2-5_TotMult"]["rows"]
    needle = bea_industry_name.strip().lower().rstrip("*")
    for row in totmult_rows:
        if row["industry_name"].strip().lower().rstrip("*") == needle:
            return row
    # Partial match fallback
    for row in totmult_rows:
        if needle in row["industry_name"].strip().lower():
            logger.debug(
                "Fuzzy TotMult match: '%s' → '%s'",
                bea_industry_name, row["industry_name"],
            )
            return row
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — SUSB payroll/sales ratio → estimated direct sales
# ─────────────────────────────────────────────────────────────────────────────

def _payroll_ratio(bea_industry_name: str) -> Tuple[float, str]:
    """Compute sector payroll-to-sales ratio from SUSB national data.

    Returns (ratio, naics_description_used).
    Walks up from BEA detailed industry → aggregate sector → NAICS 2-digit
    looking for a record that has Avg. implied sales data.

    Falls back to the "Information" sector (NAICS 51) ratio if no match found,
    and ultimately to the economy-wide average.
    """
    susb = _load_susb()
    records = susb["records"]

    # Build a quick lookup: naics_code (str, with .0) → "01: Total" record
    total_records: Dict[str, Dict] = {}
    for rec in records:
        if rec.get("ENTERPRISE EMPLOYMENT SIZE", "")[:3] == "01:":
            code = str(rec.get("NAICS   CODE", "")).strip()
            total_records[code] = rec

    def get_ratio(code: str) -> Optional[float]:
        rec = total_records.get(code)
        if rec is None:
            return None
        implied = rec.get("Avg. implied sales")
        payroll_1k = rec.get("ANNUAL PAYROLL ($1,000)")
        if not implied or str(implied) in ("-", "None", "") or not payroll_1k:
            return None
        try:
            firms = float(rec.get("NUMBER OF FIRMS") or 1)
            if firms == 0:
                return None
            payroll_per_firm = float(payroll_1k) * 1000 / firms   # $ per firm
            sales_per_firm   = float(implied)                       # $ per firm
            if sales_per_firm == 0:
                return None
            return payroll_per_firm / sales_per_firm
        except (TypeError, ValueError):
            return None

    # Identify aggregate sector for this BEA industry
    agg_sector_name = bea_industry_name.strip().lower().rstrip("*")
    naics2: Optional[str] = None
    for key, code in _BEA_TO_NAICS2.items():
        if key in agg_sector_name or agg_sector_name in key:
            naics2 = code
            break

    # Try NAICS 2-digit sector
    if naics2:
        ratio = get_ratio(naics2)
        if ratio is not None:
            desc = total_records[naics2].get("NAICS DESCRIPTION", naics2)
            logger.debug("SUSB payroll ratio %.4f from NAICS %s (%s)", ratio, naics2, desc)
            return ratio, desc

    # Fallback: "Information" sector (covers telecom / data processing)
    for fallback_code in ("51.0", "54.0", "52.0"):
        ratio = get_ratio(fallback_code)
        if ratio is not None:
            desc = total_records[fallback_code].get("NAICS DESCRIPTION", fallback_code)
            logger.warning(
                "SUSB: no payroll/sales data for '%s'; using %s (%s) as fallback. ratio=%.4f",
                bea_industry_name, fallback_code, desc, ratio,
            )
            return ratio, desc

    # Last resort: economy-wide average (NAICS "--" Total)
    rec = total_records.get("--")
    if rec:
        payroll_1k = float(rec.get("ANNUAL PAYROLL ($1,000)") or 0)
        firms = float(rec.get("NUMBER OF FIRMS") or 1)
        # No implied sales at total level — use generic 20% as backstop
    ratio = 0.20
    logger.warning("Using generic payroll/sales ratio %.2f for '%s'", ratio, bea_industry_name)
    return ratio, "economy-wide fallback"


# ─────────────────────────────────────────────────────────────────────────────
# Sector breakdown from matrix tables
# ─────────────────────────────────────────────────────────────────────────────

def _compute_sector_breakdown(
    bea_industry_code: str,
    direct_sales: float,
    mult_set: RIMSMultiplierSet,
) -> List[SectorBreakdownRow]:
    """Compute sector-by-sector impact.

    For each BEA aggregate sector row in the matrix tables, reads the column
    corresponding to *bea_industry_code* and multiplies by *direct_sales*.

    The four matrix tables map aggregate-sector rows × 64 detailed-industry columns.
    Column key = industry code string (e.g. "43.0").

    Returns one SectorBreakdownRow per aggregate sector, plus a validation
    check that column sums match the TotMult fd_* values.
    """
    col_key = bea_industry_code   # e.g. "43.0"

    # Pull column vectors from each matrix table
    def extract_col(table_key: str) -> Dict[str, float]:
        table = mult_set.tables.get(table_key, {})
        result: Dict[str, float] = {}
        for row in table.get("rows", []):
            val = row.get("multipliers_by_industry", {}).get(col_key)
            if val is not None:
                result[row["sector_code"]] = float(val)
            else:
                result[row["sector_code"]] = 0.0
        return result

    output_col    = extract_col("2-1_Output")
    earnings_col  = extract_col("2-2_Earnings")
    employ_col    = extract_col("2-3_Employ")
    val_add_col   = extract_col("2-4_ValAdd")

    # Get union of sector codes (Earnings/Employ/ValAdd have 22 rows; Output has 21)
    all_sector_codes = set(
        list(output_col.keys())
        + list(earnings_col.keys())
        + list(employ_col.keys())
        + list(val_add_col.keys())
    )

    # Get sector names from one of the tables
    sector_names: Dict[str, str] = {}
    for table_key in ("2-2_Earnings", "2-1_Output"):
        for row in mult_set.tables.get(table_key, {}).get("rows", []):
            sector_names[row["sector_code"]] = row["sector_name"]

    breakdown: List[SectorBreakdownRow] = []
    total_output    = 0.0
    total_earnings  = 0.0
    total_employ    = 0.0
    total_val_added = 0.0

    for code in sorted(all_sector_codes, key=lambda x: float(x)):
        out_mult = output_col.get(code, 0.0)
        earn_mult = earnings_col.get(code, 0.0)
        emp_mult  = employ_col.get(code, 0.0)
        va_mult   = val_add_col.get(code, 0.0)

        # Employment matrix: jobs per million dollars → scale by $M
        emp_abs = emp_mult * (direct_sales / 1_000_000)

        row = SectorBreakdownRow(
            sector_code  = code,
            sector_name  = sector_names.get(code, f"Sector {code}"),
            output       = out_mult * direct_sales,
            earnings     = earn_mult * direct_sales,
            employment   = emp_abs,
            value_added  = va_mult * direct_sales,
        )
        breakdown.append(row)
        total_output    += row.output
        total_earnings  += row.earnings
        total_employ    += row.employment
        total_val_added += row.value_added

    # Validate: column sums should approximately equal fd_* values in TotMult
    expected_output    = 0.0
    expected_earnings  = 0.0
    expected_employ    = 0.0
    expected_va        = 0.0
    for r in mult_set.tables["2-5_TotMult"]["rows"]:
        if r["industry_code"] == col_key:
            expected_output   = (r["fd_output"]     or 0.0) * direct_sales
            expected_earnings = (r["fd_earnings"]   or 0.0) * direct_sales
            expected_employ   = (r["fd_employment"] or 0.0) * (direct_sales / 1_000_000)
            expected_va       = (r["fd_value_added"]or 0.0) * direct_sales
            break

    def _pct_diff(a: float, b: float) -> float:
        if b == 0:
            return 0.0
        return abs(a - b) / abs(b) * 100

    if _pct_diff(total_output, expected_output) > 2.0:
        logger.warning(
            "Sector breakdown output sum $%.0f differs from TotMult fd_output "
            "expectation $%.0f (%.1f%% gap). Column %s may be misaligned.",
            total_output, expected_output, _pct_diff(total_output, expected_output), col_key,
        )
    else:
        logger.debug(
            "Sector breakdown validated: output $%.0f ≈ fd_output expectation $%.0f",
            total_output, expected_output,
        )

    return breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Operations
# ─────────────────────────────────────────────────────────────────────────────

def compute_operations(
    inputs: ProjectEconomicInputs,
    mult_set: RIMSMultiplierSet,
    warnings: List[str],
) -> Tuple[OperationsImpact, List[SectorBreakdownRow]]:
    """
    Seven-step operations phase.

    Step 1: Map user sector → BEA 64-industry name
    Step 2: Load TotMult row for that industry
    Step 3: Total jobs = direct_jobs × de_employment multiplier
    Step 4: Total earnings = direct_earnings × de_earnings multiplier
    Step 5: Estimate direct sales via SUSB payroll/sales ratio
    Step 6: Total output = estimated_sales × fd_output multiplier
    Step 7: Total value-added = estimated_sales × fd_value_added multiplier
    """

    # ── Step 1 ────────────────────────────────────────────────────────────────
    bea_name = _map_sector(inputs.sector)
    if bea_name is None:
        msg = (
            f"Sector '{inputs.sector}' not found in crosswalk. "
            "Using 'Professional, scientific, and technical services' as fallback."
        )
        logger.warning(msg)
        warnings.append(msg)
        bea_name = "Professional, scientific, and technical services"

    # ── Step 2 ────────────────────────────────────────────────────────────────
    totmult_row = _find_totmult_row(bea_name, mult_set)
    if totmult_row is None:
        raise ValueError(
            f"BEA industry '{bea_name}' not found in RIMS II TotMult table for {mult_set.state}."
        )

    bea_code = totmult_row["industry_code"]
    de_employment = totmult_row["de_employment"] or 0.0
    de_earnings   = totmult_row["de_earnings"]   or 0.0
    fd_output     = totmult_row["fd_output"]     or 0.0
    fd_earnings   = totmult_row["fd_earnings"]   or 0.0
    fd_employment = totmult_row["fd_employment"] or 0.0
    fd_value_added= totmult_row["fd_value_added"]or 0.0

    logger.debug(
        "Industry '%s' (code %s): de_employ=%.4f  fd_output=%.4f  fd_value_added=%.4f",
        bea_name, bea_code, de_employment, fd_output, fd_value_added,
    )

    # ── Step 3 ────────────────────────────────────────────────────────────────
    total_jobs = inputs.direct_jobs * de_employment

    # ── Step 4 ────────────────────────────────────────────────────────────────
    total_earnings = inputs.direct_earnings * de_earnings

    # ── Step 5 ────────────────────────────────────────────────────────────────
    payroll_ratio, ratio_source = _payroll_ratio(bea_name)
    if payroll_ratio <= 0:
        payroll_ratio = 0.20
        warnings.append("Payroll/sales ratio unavailable; using 20% fallback.")

    estimated_direct_sales = inputs.direct_earnings / payroll_ratio
    logger.debug(
        "Payroll/sales ratio %.4f (source: %s) → estimated direct sales $%.0f",
        payroll_ratio, ratio_source, estimated_direct_sales,
    )

    # ── Step 6 ────────────────────────────────────────────────────────────────
    total_output = estimated_direct_sales * fd_output

    # ── Step 7 ────────────────────────────────────────────────────────────────
    total_value_added = estimated_direct_sales * fd_value_added

    ops = OperationsImpact(
        direct_jobs              = inputs.direct_jobs,
        direct_earnings          = inputs.direct_earnings,
        direct_sales_estimated   = estimated_direct_sales,
        bea_industry_code        = bea_code,
        bea_industry_name        = totmult_row["industry_name"],
        de_employment_mult       = de_employment,
        de_earnings_mult         = de_earnings,
        fd_output_mult           = fd_output,
        fd_earnings_mult         = fd_earnings,
        fd_employment_mult       = fd_employment,
        fd_value_added_mult      = fd_value_added,
        total_jobs               = total_jobs,
        total_earnings           = total_earnings,
        total_output             = total_output,
        total_value_added        = total_value_added,
    )

    # ── Sector breakdown ──────────────────────────────────────────────────────
    breakdown = _compute_sector_breakdown(bea_code, estimated_direct_sales, mult_set)

    return ops, breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Construction
# ─────────────────────────────────────────────────────────────────────────────

_CONSTRUCTION_BEA_NAME = "Construction"


def compute_construction(
    inputs: ProjectEconomicInputs,
    mult_set: RIMSMultiplierSet,
    warnings: List[str],
) -> ConstructionImpact:
    """
    Three-step construction phase.

    Step 1: Step-down capex into materials / soft costs / labor (wages + benefits).
    Step 2: Apply capture rates to each category.
    Step 3: Apply RIMS II Construction row fd_* multipliers to total captured capex.
    """

    splits = inputs.construction_splits
    capture = inputs.capture_rates

    capex = inputs.capex

    # ── Step 1: Allocate capex ────────────────────────────────────────────────
    materials_total  = capex * splits.get("materials",  0.40)
    soft_costs_total = capex * splits.get("soft_costs", 0.10)
    labor_total      = capex * splits.get("labor",      0.50)
    labor_wages_total    = labor_total * inputs.labor_wage_share    # default 70%
    labor_benefits_total = labor_total * inputs.labor_benefit_share # default 30%

    # ── Step 2: Apply capture rates ──────────────────────────────────────────
    materials_captured      = materials_total      * capture.get("materials",      0.3184)
    soft_costs_captured     = soft_costs_total     * capture.get("soft_costs",     1.00)
    labor_wages_captured    = labor_wages_total    * capture.get("labor_wages",    1.00)
    labor_benefits_captured = labor_benefits_total * capture.get("labor_benefits", 0.35)
    total_captured = (
        materials_captured
        + soft_costs_captured
        + labor_wages_captured
        + labor_benefits_captured
    )

    logger.debug(
        "Construction capture: materials=$%.0f  soft=$%.0f  labor_wages=$%.0f  "
        "labor_benefits=$%.0f  total=$%.0f  (capex=$%.0f)",
        materials_captured, soft_costs_captured,
        labor_wages_captured, labor_benefits_captured,
        total_captured, capex,
    )

    # ── Step 3: Apply RIMS II Construction multipliers ────────────────────────
    totmult_row = _find_totmult_row(_CONSTRUCTION_BEA_NAME, mult_set)
    if totmult_row is None:
        warnings.append("Construction row not found in TotMult; construction impact set to zero.")
        fd_output = fd_earnings = fd_employment = fd_value_added = 0.0
        bea_code = "7.0"
        bea_name = _CONSTRUCTION_BEA_NAME
    else:
        bea_code      = totmult_row["industry_code"]
        bea_name      = totmult_row["industry_name"]
        fd_output     = totmult_row["fd_output"]      or 0.0
        fd_earnings   = totmult_row["fd_earnings"]    or 0.0
        fd_employment = totmult_row["fd_employment"]  or 0.0
        fd_value_added= totmult_row["fd_value_added"] or 0.0

    total_constr_output     = total_captured * fd_output
    total_constr_earnings   = total_captured * fd_earnings
    total_constr_value_added= total_captured * fd_value_added
    # Employment: fd_employment is jobs per million dollars
    total_constr_jobs = (total_captured / 1_000_000) * fd_employment

    return ConstructionImpact(
        capex                    = capex,
        materials_captured       = materials_captured,
        soft_costs_captured      = soft_costs_captured,
        labor_wages_captured     = labor_wages_captured,
        labor_benefits_captured  = labor_benefits_captured,
        total_captured           = total_captured,
        bea_industry_code        = bea_code,
        bea_industry_name        = bea_name,
        fd_output_mult           = fd_output,
        fd_earnings_mult         = fd_earnings,
        fd_employment_mult       = fd_employment,
        fd_value_added_mult      = fd_value_added,
        total_jobs               = total_constr_jobs,
        total_earnings           = total_constr_earnings,
        total_output             = total_constr_output,
        total_value_added        = total_constr_value_added,
    )
