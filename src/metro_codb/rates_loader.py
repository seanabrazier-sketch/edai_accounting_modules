"""
metro_codb/rates_loader.py
Loads all data/codb/ JSON files at startup and constructs:
  - One MetroRates object per metro
  - Three ProjectArchetype objects (office, manufacturing, distribution)

Public API:
  get_metro_rates(metro_name: str)  -> MetroRates
  get_all_metros()                  -> list[str]
  get_archetype(name: str)          -> ProjectArchetype
  get_all_archetypes()              -> list[ProjectArchetype]

Data sources:
  dyn_oews_msa_2022.json         BLS OEWS 2022 MSA wages (primary)
  dyn_oews_state_2022.json       BLS OEWS 2022 state wages (fallback L2)
  dyn_oews_national_2022.json    BLS OEWS 2022 national wages (fallback L3)
  dyn_real_estate_clean.json     CommercialEdge/CoStar 2023 rents
  dyn_utility_rates_msa.json     EIA $/kWh by MSA area (commercial + industrial)
  sea_water_sewer_computed.json  Metro water/sewer monthly charges
  dyn_water_sewer.json           State-level water/sewer fallback
  dyn_state_and_local_taxes.json EY/COST FY2022 effective state+local tax rates
  dyn_workers_comp_reformat.json Oregon 2024 workers comp rates by state
  dyn_state_ui_rates.json        DOL SUI rates by state (per FTE annual)
  kff_single_health_premiums.json  KFF 2024 single-coverage employer contribution by state
  whitepaper_metros.json         Canonical 100-metro whitepaper universe (from PnL Office tab)
  sea_lincoln_prop_tax.json      Lincoln Institute 2019 commercial property tax rates
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from typing import Optional

from .models import MetroRates, ProjectArchetype

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(__file__)
_DATA_DIR = os.path.join(_HERE, "..", "..", "data", "codb")


def _data(filename: str) -> str:
    return os.path.join(_DATA_DIR, filename)


def _load(filename: str) -> list:
    path = _data(filename)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Module-level caches (populated on first call to _ensure_loaded())
# ---------------------------------------------------------------------------

_metro_rates: dict[str, MetroRates] = {}          # metro_name → MetroRates
_archetypes:  dict[str, ProjectArchetype] = {}    # name → ProjectArchetype
_loaded = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_metro_rates(metro_name: str) -> MetroRates:
    """Return MetroRates for the given metro name (exact or close match)."""
    _ensure_loaded()
    # Exact match first
    if metro_name in _metro_rates:
        return _metro_rates[metro_name]
    # Case-insensitive match
    lower = metro_name.lower()
    for k, v in _metro_rates.items():
        if k.lower() == lower:
            return v
    raise KeyError(f"Metro not found: '{metro_name}'. Use get_all_metros() to list available metros.")


def get_all_metros() -> list[str]:
    """Return sorted list of all available metro names."""
    _ensure_loaded()
    return sorted(_metro_rates.keys())


def get_archetype(name: str) -> ProjectArchetype:
    """Return ProjectArchetype by name ('office'|'manufacturing'|'distribution')."""
    _ensure_loaded()
    name_lower = name.lower()
    if name_lower in _archetypes:
        return _archetypes[name_lower]
    raise KeyError(f"Archetype '{name}' not found. Choose from: {list(_archetypes.keys())}")


def get_all_archetypes() -> list[ProjectArchetype]:
    """Return all three ProjectArchetype objects."""
    _ensure_loaded()
    return list(_archetypes.values())


# ---------------------------------------------------------------------------
# Internal loader
# ---------------------------------------------------------------------------

def _ensure_loaded() -> None:
    global _loaded
    if not _loaded:
        _load_all()
        _loaded = True


def _load_all() -> None:
    """Load all data sources and populate _metro_rates and _archetypes."""
    logger.info("Loading Metro CODB data from %s …", _DATA_DIR)

    # -----------------------------------------------------------------------
    # 1. Build lookup tables from each data source
    # -----------------------------------------------------------------------

    # 1a. OEWS wages — three tiers
    wages_msa    = _build_oews_lookup("dyn_oews_msa_2022.json",     key_col="Metro_Occ_group")
    wages_state  = _build_oews_lookup("dyn_oews_state_2022.json",   key_col="State_occ_group")
    wages_natl   = _build_oews_lookup("dyn_oews_national_2022.json", key_col="Area_occ_group")

    # 1a-ii. Build CBSA prefix map: (first_city_lower, state_abb) → CBSA prefix
    #   OEWS MSA keys use CBSA format "Seattle-Tacoma-Bellevue, WA_Occupation_level"
    #   but real estate city_state uses "Seattle, Washington".
    #   We map city name → CBSA to enable MSA-level wage lookup.
    cbsa_prefix_map = _build_cbsa_prefix_map(wages_msa)

    # 1b. Real estate rents — keyed by "City_state" (e.g. "Seattle, Washington")
    re_by_city  = _build_re_lookup()

    # 1c. Electricity rates — keyed by EMSI area label
    elec_by_area = _build_elec_lookup()

    # 1d. Water/sewer — metro level, then state-level fallback
    ws_by_city   = _build_ws_lookup()
    ws_by_state  = _build_ws_state_lookup()

    # 1e. State/local effective tax rates
    sl_tax_by_state = _build_sl_tax_lookup()

    # 1f. Workers comp — by state abbreviation, class 8810 (office/clerical)
    #     class 9015 = manufacturing
    wc_by_state_class = _build_wc_lookup()

    # 1g. SUI annual per FTE by state (full state name)
    sui_by_state = _build_sui_lookup()

    # 1h. Health premiums — KFF 2024 single coverage employer contribution by state
    health_by_state = _build_health_lookup()

    # 1i. Property tax by state
    prop_tax_by_state = _build_prop_tax_lookup()

    # 1j. State abbreviation ↔ full name maps (built from UI data)
    abb_to_name, name_to_abb = _build_state_maps()

    # 1k. Whitepaper metro universe (100 metros from PnL Office tab of Seattle CODB comps)
    whitepaper_set = set(_load("whitepaper_metros.json"))
    logger.info("Whitepaper universe: %d metros", len(whitepaper_set))

    # -----------------------------------------------------------------------
    # 2. Enumerate metros from real estate data, filtered to whitepaper universe
    # -----------------------------------------------------------------------
    re_data = _load("dyn_real_estate_clean.json")
    n_skipped = 0

    for rec in re_data:
        city_state = rec.get("City_state")
        if not city_state:
            continue
        city_state = city_state.strip()

        # Filter to whitepaper universe
        if city_state not in whitepaper_set:
            n_skipped += 1
            continue

        # Derive state from "City, State" pattern
        state_full, state_abb = _derive_state(city_state, abb_to_name, name_to_abb)

        mr = MetroRates(
            metro_name  = city_state,
            emsi_area   = "",   # filled in from utility/wage data when available
            state       = state_full,
            state_abbrev = state_abb,
        )

        # -- Wages ----------------------------------------------------------
        _attach_wages(mr, city_state, state_full, state_abb,
                      wages_msa, wages_state, wages_natl, cbsa_prefix_map)

        # -- Real estate ----------------------------------------------------
        o_rent = _safe_float(rec.get("blended_office_rent_psf") or rec.get("office_rent_psf"))
        i_rent = _safe_float(rec.get("industrial_net_rent_psf_yr"))
        mr.office_rent_sqft      = o_rent
        mr.office_rent_source    = "CommercialEdge/CoStar 2023"
        mr.industrial_rent_sqft  = i_rent
        mr.industrial_rent_source = "CommercialEdge 2023"

        # -- Electricity ----------------------------------------------------
        _attach_electricity(mr, city_state, elec_by_area, state_abb, abb_to_name)

        # -- Water/sewer ----------------------------------------------------
        _attach_water_sewer(mr, city_state, ws_by_city, ws_by_state, state_full)

        # -- Property tax ---------------------------------------------------
        _attach_prop_tax(mr, state_full, prop_tax_by_state)

        # -- State & local tax ----------------------------------------------
        _attach_sl_tax(mr, state_full, sl_tax_by_state)

        # -- Workers comp ---------------------------------------------------
        _attach_wc(mr, state_abb, wc_by_state_class)

        # -- SUI ------------------------------------------------------------
        _attach_sui(mr, state_full, sui_by_state)

        # -- Health premiums ------------------------------------------------
        _attach_health(mr, state_full, health_by_state)

        _metro_rates[city_state] = mr

    logger.info(
        "Loaded %d metros (%d outside whitepaper universe skipped).",
        len(_metro_rates), n_skipped,
    )

    # -----------------------------------------------------------------------
    # 3. Build the three ProjectArchetype objects
    # -----------------------------------------------------------------------
    _archetypes["office"]       = _build_office_archetype()
    _archetypes["manufacturing"] = _build_manufacturing_archetype()
    _archetypes["distribution"] = _build_distribution_archetype()

    logger.info("Archetypes: %s", list(_archetypes.keys()))


# ---------------------------------------------------------------------------
# Lookup builders
# ---------------------------------------------------------------------------

def _build_cbsa_prefix_map(wages_msa: dict) -> dict[tuple, str]:
    """Build a mapping (first_city_lower, state_abb_upper) → CBSA prefix.

    The OEWS MSA keys look like:
      "Seattle-Tacoma-Bellevue, WA_General and Operations Managers_detailed"
    We extract the CBSA prefix "Seattle-Tacoma-Bellevue, WA" and index it by
    the first city name and state abbreviation so we can look up wages for
    any metro given its city name and state abbreviation.

    Example:
      ("seattle", "WA") → "Seattle-Tacoma-Bellevue, WA"
      ("fort smith", "AR") → "Fort Smith, AR"
    """
    cbsa_prefixes: set[str] = set()
    for key in wages_msa:
        # Key format: "{CBSA}_{Occupation}_{level}"
        # CBSA itself may contain spaces and commas but not underscores.
        # Split on underscore and the CBSA is everything before the last two segments.
        parts = key.split("_")
        if len(parts) >= 3:
            cbsa = "_".join(parts[:-2])
            cbsa_prefixes.add(cbsa)

    cbsa_map: dict[tuple, str] = {}
    city_only_map: dict[str, str] = {}   # fallback if state abb not uniquely matched

    for prefix in cbsa_prefixes:
        # prefix like "Seattle-Tacoma-Bellevue, WA" or "Fort Smith, AR"
        comma_idx = prefix.rfind(",")
        if comma_idx < 0:
            continue
        city_part  = prefix[:comma_idx].strip()         # "Seattle-Tacoma-Bellevue"
        state_part = prefix[comma_idx + 1:].strip()     # "WA" or "MO-KS" (bi-state)
        # Take only the first state abbreviation for bi-state CBSAs
        state_abb  = state_part.split("-")[0].strip().upper()   # "WA"
        first_city = city_part.split("-")[0].strip().lower()    # "seattle"

        cbsa_map[(first_city, state_abb)] = prefix
        if first_city not in city_only_map:
            city_only_map[first_city] = prefix

    # Store both dicts as a tuple-keyed dict with a special sentinel for fallback
    # We combine into one dict using a _fallback_ key prefix for city-only entries
    for city, prefix in city_only_map.items():
        cbsa_map[("_city_", city)] = prefix

    return cbsa_map


def _resolve_cbsa_prefix(
    city_state: str,
    state_abb: str,
    cbsa_map: dict,
) -> str:
    """Return the CBSA prefix for a given city_state string, or '' if not found.

    Tries (first_city, state_abb) first, then city-only fallback.
    """
    city_raw = city_state.split(",")[0].strip().lower()
    return (
        cbsa_map.get((city_raw, state_abb.upper()))
        or cbsa_map.get(("_city_", city_raw))
        or ""
    )


def _build_oews_lookup(filename: str, key_col: str) -> dict[str, float]:
    """Return dict: key → A_MEDIAN wage.

    Keys for MSA file look like: "Seattle, Washington_Management Occupations_major"
    Keys for State file:          "Washington_Management Occupations_major"
    Keys for National file:       "US_Management Occupations_major"
    """
    data = _load(filename)
    out: dict[str, float] = {}
    for rec in data:
        k = rec.get(key_col)
        v = rec.get("A_MEDIAN")
        if k and v is not None:
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def _build_re_lookup() -> dict[str, dict]:
    """Keyed by city_state (lower-cased for matching)."""
    data = _load("dyn_real_estate_clean.json")
    return {r["City_state"].strip().lower(): r for r in data if r.get("City_state")}


def _build_elec_lookup() -> dict[str, dict]:
    """Keyed by EMSI area label (lower-cased)."""
    data = _load("dyn_utility_rates_msa.json")
    out: dict[str, dict] = {}
    for r in data:
        area = r.get("emsi_area")
        if area and isinstance(area, str) and area != "EMSI area":
            out[area.strip().lower()] = r
    return out


def _build_ws_lookup() -> dict[str, dict]:
    """Metro-level water/sewer. Keyed by city_state lower-cased."""
    data = _load("sea_water_sewer_computed.json")
    return {r["city_state"].strip().lower(): r for r in data if r.get("city_state")}


def _build_ws_state_lookup() -> dict[str, dict]:
    """State-level water/sewer. Keyed by state full name lower-cased."""
    data = _load("dyn_water_sewer.json")
    out: dict[str, dict] = {}
    for r in data:
        s = r.get("state")
        if s:
            out[s.strip().lower()] = r
    return out


def _build_sl_tax_lookup() -> dict[str, float]:
    """State full name → EY COST FY2022 effective rate."""
    data = _load("dyn_state_and_local_taxes.json")
    out: dict[str, float] = {}
    for rec in data:
        state = rec.get("col_0")
        rate  = rec.get("col_1")
        if (state and isinstance(state, str)
                and state not in ("State", "Year >>>", "Source >>>", "Category >>>")
                and rate is not None and isinstance(rate, float)):
            out[state.strip().lower()] = rate
    return out


def _build_wc_lookup() -> dict[str, float]:
    """(state_abb, class_code) → rate per $1 payroll.

    The reformatted table has 'State' (abbrev), 'Rate per 100 USD of payroll',
    and 'State_class' (e.g. 'WA_9015').
    """
    data = _load("dyn_workers_comp_reformat.json")
    out: dict[tuple, float] = {}
    for rec in data:
        abb   = rec.get("State")
        rate  = rec.get("Rate per 100 USD of payroll")
        sc    = rec.get("State_class", "")
        if abb and rate is not None:
            class_code = sc.split("_")[-1] if "_" in sc else ""
            out[(abb.upper(), class_code)] = float(rate) / 100.0  # convert to per-$1
    return out


def _build_sui_lookup() -> dict[str, float]:
    """State full name → annual SUI per FTE (USD).

    The Dynamic State UI Rates table (dyn_state_ui_rates.json) has:
    col_1=State, col_5=Per FTE UI payment ($) for 2022.
    """
    data = _load("dyn_state_ui_rates.json")
    out: dict[str, float] = {}
    # Find data rows — header row has col_1='Geography' and col_5='Per FTE UI payment ($)'
    in_data = False
    for rec in data:
        c1 = rec.get("col_1")
        c5 = rec.get("col_5")
        if c1 == "Geography" and c5 is not None:
            in_data = True
            continue
        if in_data and c1 and isinstance(c1, str) and c5 is not None:
            # Stop at next section header
            if c1 in ("United States", "Geography"):
                continue
            try:
                out[c1.strip().lower()] = float(c5)
            except (TypeError, ValueError):
                pass
    return out


def _build_health_lookup() -> dict[str, float]:
    """State full name (lower) → KFF 2024 employer single-coverage premium (USD/yr).

    Source: kff_single_health_premiums.json
      Derived from KFF 2024 "Average Annual Single Premium per Enrolled Employee
      for Employer-Based Health Insurance", employer contribution column.
      National average: $6,697/yr.

    E-Fix note: switched from MEPS family-coverage ($14,500 avg) to KFF single-coverage
    ($6,697 avg) to match the source data used in the original whitepaper model.
    """
    data = _load("kff_single_health_premiums.json")
    # National-level fallback value
    natl_fallback: Optional[float] = None
    out: dict[str, float] = {}
    for rec in data:
        state = rec.get("state")
        val   = rec.get("employer_single_premium")
        if state and val is not None:
            key = state.strip().lower()
            out[key] = float(val)
            if state == "United States":
                natl_fallback = float(val)
    # Store national fallback for states not found
    if natl_fallback is not None:
        out["_national_"] = natl_fallback
    return out


def _build_prop_tax_lookup() -> dict[str, float]:
    """State full name (lower) → commercial property tax rate (Lincoln Inst 2019).

    The source uses abbreviated state names in some cases (e.g., "DC" for
    District of Columbia and "AVERAGE" for the national average row).
    We map both the raw key and any known expansions.
    """
    _abbrev_expansions = {
        "dc": "district of columbia",
    }
    data = _load("sea_lincoln_prop_tax.json")
    out: dict[str, float] = {}
    for r in data:
        state_raw = r.get("state", "")
        rate = r.get("commercial_prop_tax_rate")
        if not state_raw or rate is None:
            continue
        key = state_raw.strip().lower()
        out[key] = rate
        # Also index under expanded name if abbreviation recognised
        expanded = _abbrev_expansions.get(key)
        if expanded:
            out[expanded] = rate
    return out


def _build_state_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Build abbreviation → full name and full name → abbreviation maps.

    Source: dyn_workers_comp_reformat.json has state abbreviations.
    We supplement with a hardcoded reference table for full name mapping.
    """
    # Hardcoded US state abbreviation ↔ name map
    abb_to_name = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
        "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
        "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
        "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    }
    name_to_abb = {v.lower(): k for k, v in abb_to_name.items()}
    return abb_to_name, name_to_abb


# ---------------------------------------------------------------------------
# Attach helpers — populate MetroRates fields from lookup tables
# ---------------------------------------------------------------------------

# Occupation → SOC major group for OEWS lookup
# When a detailed occupation isn't in OEWS by name, fall back to its major group
_OCCUPATION_TO_SOC_MAJOR: dict[str, str] = {
    "General and Operations Managers":                 "Management Occupations",
    "Human Resources Managers":                        "Management Occupations",
    "Industrial Production Managers":                  "Management Occupations",
    "Transportation, Storage, and Distribution Managers": "Management Occupations",
    "Buyers and Purchasing Agents":                    "Business and Financial Operations Occupations",
    "Claims Adjusters, Examiners, and Investigators":  "Business and Financial Operations Occupations",
    "Accountants and Auditors":                        "Business and Financial Operations Occupations",
    "Financial and Investment Analysts":               "Business and Financial Operations Occupations",
    "Database Administrators":                         "Computer and Mathematical Occupations",
    "Computer User Support Specialists":               "Computer and Mathematical Occupations",
    "Industrial Engineers":                            "Architecture and Engineering Occupations",
    "Sales Representatives of Services, Except Advertising, Insurance, Financial Services, and Travel":
                                                       "Sales and Related Occupations",
    "Bookkeeping, Accounting, and Auditing Clerks":    "Office and Administrative Support Occupations",
    "Customer Service Representatives":                "Office and Administrative Support Occupations",
    "First-Line Supervisors of Office and Administrative Support Workers":
                                                       "Office and Administrative Support Occupations",
    "Office Clerks, General":                          "Office and Administrative Support Occupations",
    "Shipping, Receiving, and Inventory Clerks":       "Office and Administrative Support Occupations",
    "Receptionists and Information Clerks":            "Office and Administrative Support Occupations",
    "Maintenance Workers, Machinery":                  "Installation, Maintenance, and Repair Occupations",
    "First-Line Supervisors of Production and Operating Workers":
                                                       "Production Occupations",
    "Miscellaneous Assemblers and Fabricators":        "Production Occupations",
    "Computer Numerically Controlled Tool Operators":  "Production Occupations",
    "Machinists":                                      "Production Occupations",
    "Tool and Die Makers":                             "Production Occupations",
    "Welders, Cutters, Solderers, and Brazers":        "Production Occupations",
    "Inspectors, Testers, Sorters, Samplers, and Weighers":
                                                       "Production Occupations",
    "Stockers and Order Fillers":                      "Transportation and Material Moving Occupations",
    "First-Line Supervisors of Transportation and Material Moving Workers, Except Aircraft Cargo Handling Supervisors":
                                                       "Transportation and Material Moving Occupations",
    "Heavy and Tractor-Trailer Truck Drivers":         "Transportation and Material Moving Occupations",
    "Industrial Truck and Tractor Operators":          "Transportation and Material Moving Occupations",
    "Laborers and Freight, Stock, and Material Movers, Hand":
                                                       "Transportation and Material Moving Occupations",
    "Packers and Packagers, Hand":                     "Transportation and Material Moving Occupations",
}


def _attach_wages(
    mr: MetroRates,
    city_state: str,
    state_full: str,
    state_abb: str,
    wages_msa: dict,
    wages_state: dict,
    wages_natl: dict,
    cbsa_prefix_map: dict,
) -> None:
    """Populate wages_by_occupation and wages_source using three-tier fallback.

    OEWS MSA keys use CBSA format (e.g. "Seattle-Tacoma-Bellevue, WA"), while
    real estate data uses city+state name format (e.g. "Seattle, Washington").
    We resolve the CBSA prefix via cbsa_prefix_map before constructing keys.
    """
    all_occupations = set(_OCCUPATION_TO_SOC_MAJOR.keys())

    # Resolve CBSA prefix for MSA lookup
    cbsa_prefix = _resolve_cbsa_prefix(city_state, state_abb, cbsa_prefix_map)
    if cbsa_prefix:
        mr.emsi_area = mr.emsi_area or cbsa_prefix  # store for reference

    # Build key prefixes
    city_prefix  = cbsa_prefix + "_" if cbsa_prefix else ""
    state_prefix = state_full + "_"
    natl_prefix  = "US_"

    for occ in all_occupations:
        soc_major = _OCCUPATION_TO_SOC_MAJOR.get(occ, "")

        # --- Tier 1: MSA detailed occupation (requires resolved CBSA prefix) ---
        if city_prefix:
            key_msa_det = f"{city_prefix}{occ}_detailed"
            wage = wages_msa.get(key_msa_det)
            if wage is not None:
                mr.wages_by_occupation[occ] = wage
                mr.wages_source[occ] = "MSA"
                continue

            # --- Tier 1b: MSA major group ---
            key_msa_maj = f"{city_prefix}{soc_major}_major"
            wage = wages_msa.get(key_msa_maj)
            if wage is not None:
                mr.wages_by_occupation[occ] = wage
                mr.wages_source[occ] = "MSA_major"
                continue

        # --- Tier 2: State detailed ---
        key_state_det = f"{state_prefix}{occ}_detailed"
        wage = wages_state.get(key_state_det)
        if wage is not None:
            mr.wages_by_occupation[occ] = wage
            mr.wages_source[occ] = "State"
            continue

        # --- Tier 2b: State major ---
        key_state_maj = f"{state_prefix}{soc_major}_major"
        wage = wages_state.get(key_state_maj)
        if wage is not None:
            mr.wages_by_occupation[occ] = wage
            mr.wages_source[occ] = "State_major"
            continue

        # --- Tier 3: National detailed ---
        key_natl_det = f"{natl_prefix}{occ}_detailed"
        wage = wages_natl.get(key_natl_det)
        if wage is not None:
            mr.wages_by_occupation[occ] = wage
            mr.wages_source[occ] = "National"
            continue

        # --- Tier 3b: National major ---
        key_natl_maj = f"{natl_prefix}{soc_major}_major"
        wage = wages_natl.get(key_natl_maj)
        if wage is not None:
            mr.wages_by_occupation[occ] = wage
            mr.wages_source[occ] = "National_major"
            continue

        # Missing
        logger.debug(
            "Metro '%s': wage missing for '%s' (SOC: %s)",
            city_state, occ, soc_major,
        )


def _attach_electricity(
    mr: MetroRates,
    city_state: str,
    elec_by_area: dict,
    state_abb: str,
    abb_to_name: dict,
) -> None:
    """Match city_state → EMSI area label → EIA electricity rate.

    The EMSI area labels look like "Seattle-Tacoma-Bellevue, WA Metro Area".
    We try several fuzzy patterns to match "Seattle, Washington" → the EMSI label.
    """
    # Extract city name and state from city_state
    parts = city_state.split(",", 1)
    city_raw  = parts[0].strip()
    state_raw = parts[1].strip() if len(parts) > 1 else ""

    # Build candidate EMSI area patterns
    candidates = []
    for area_lower, rec in elec_by_area.items():
        area_orig = rec.get("emsi_area", "")
        # Match if city name appears at start of EMSI area label
        if city_raw.lower() in area_lower:
            candidates.append((area_orig, rec))

    if candidates:
        # Pick the best (shortest — most specific to our city)
        area_orig, rec = min(candidates, key=lambda x: len(x[0]))
        comm = _safe_float(rec.get("comm_rate"))
        ind  = _safe_float(rec.get("ind_rate"))
        if comm:
            mr.electricity_rate_commercial = comm
            mr.electricity_rate_commercial_source = (
                f"EIA via Utility rates MSA: {area_orig}"
            )
        if ind:
            mr.electricity_rate_industrial = ind
            mr.electricity_rate_industrial_source = (
                f"EIA via Utility rates MSA: {area_orig}"
            )
        if mr.emsi_area == "":
            mr.emsi_area = area_orig

    if mr.electricity_rate_commercial is None:
        logger.debug(
            "Metro '%s': no electricity rate found in EIA MSA data (city='%s')",
            city_state, city_raw,
        )


def _attach_water_sewer(
    mr: MetroRates,
    city_state: str,
    ws_by_city: dict,
    ws_by_state: dict,
    state_full: str,
) -> None:
    """Attach water/sewer monthly charges.

    Priority:
      1. Metro-level from Seattle CODB Water and Sewer Data (city_state key)
      2. State-level average from Dynamic Water sewer average
    Annual cost = monthly × 12 (done in codb_engine.py).
    """
    key = city_state.strip().lower()
    rec = ws_by_city.get(key)

    if rec:
        # Metro-level data available
        office_total = _add_optional(
            _safe_float(rec.get("water_monthly_20ccf")),
            _safe_float(rec.get("sewer_monthly_20ccf")),
        )
        manuf_total = _add_optional(
            _safe_float(rec.get("water_monthly_1337ccf")),
            _safe_float(rec.get("sewer_monthly_1337ccf")),
        )
        if office_total is not None:
            mr.water_sewer_monthly_office = office_total
        if manuf_total is not None:
            mr.water_sewer_monthly_manuf = manuf_total
        mr.water_sewer_source = f"Metro-level: Seattle CODB comps Water and Sewer Data ({city_state})"
    else:
        # State-level fallback
        state_rec = ws_by_state.get(state_full.lower())
        if state_rec:
            o = _add_optional(
                _safe_float(state_rec.get("water_monthly_20ccf")),
                _safe_float(state_rec.get("sewer_monthly_20ccf")),
            )
            m = _add_optional(
                _safe_float(state_rec.get("water_monthly_1337ccf")),
                _safe_float(state_rec.get("sewer_monthly_1337ccf")),
            )
            if o is not None:
                mr.water_sewer_monthly_office = o
            if m is not None:
                mr.water_sewer_monthly_manuf = m
            mr.water_sewer_source = f"State fallback: {state_full}"
        else:
            logger.debug(
                "Metro '%s': no water/sewer data (state='%s')", city_state, state_full
            )
            mr.water_sewer_source = "MISSING"


def _attach_prop_tax(
    mr: MetroRates,
    state_full: str,
    prop_tax_by_state: dict,
) -> None:
    rate = prop_tax_by_state.get(state_full.lower())
    if rate is not None:
        mr.property_tax_rate = rate
        mr.property_tax_source = f"Lincoln Institute 2019, commercial, {state_full}"
    else:
        logger.debug("Metro '%s': no property tax for state '%s'", mr.metro_name, state_full)


def _attach_sl_tax(
    mr: MetroRates,
    state_full: str,
    sl_tax_by_state: dict,
) -> None:
    rate = sl_tax_by_state.get(state_full.lower())
    if rate is not None:
        mr.state_local_tax_rate = rate
        mr.state_local_tax_source = f"EY/COST FY2022, {state_full}"
    else:
        logger.debug("No S/L tax rate for state '%s'", state_full)


def _attach_wc(
    mr: MetroRates,
    state_abb: str,
    wc_by_state_class: dict,
) -> None:
    """Workers comp rate.

    Class codes:
      8810 = Clerical Office (office archetype)
      9015 = Buildings–Operation (used for manufacturing in existing data)
    We store the class 8810 (office) rate since that's the most commonly
    available class. The engine applies this to all archetypes. A future
    enhancement could use different classes per archetype.
    """
    # Try class 8810 first (clerical/office), then 9015 (manufacturing)
    for cls in ("8810", "9015"):
        rate = wc_by_state_class.get((state_abb.upper(), cls))
        if rate is not None:
            mr.workers_comp_rate = rate
            mr.workers_comp_source = f"Oregon 2024 study, class {cls}, {state_abb}"
            return
    logger.debug("No workers comp rate for state_abb='%s'", state_abb)


def _attach_sui(
    mr: MetroRates,
    state_full: str,
    sui_by_state: dict,
) -> None:
    val = sui_by_state.get(state_full.lower())
    if val is not None:
        mr.sui_annual_per_fte = val
        mr.sui_source = f"DOL SUI 2022, {state_full}"
    else:
        logger.debug("No SUI for state '%s'", state_full)


def _attach_health(
    mr: MetroRates,
    state_full: str,
    health_by_state: dict,
) -> None:
    """Attach KFF 2024 single-coverage employer premium per FTE.

    Falls back to national average ($6,697) if state not found.
    """
    val = health_by_state.get(state_full.lower())
    if val is not None:
        mr.health_premium_per_fte = val
        mr.health_premium_source = f"KFF 2024 single coverage, {state_full}"
    else:
        # Use national average fallback
        natl = health_by_state.get("_national_")
        if natl is not None:
            mr.health_premium_per_fte = natl
            mr.health_premium_source = "KFF 2024 single coverage, national avg fallback"
        else:
            logger.debug("No health premium for state '%s'", state_full)


# ---------------------------------------------------------------------------
# Archetype constructors
# ---------------------------------------------------------------------------

def _build_office_archetype() -> ProjectArchetype:
    """50-person professional/office archetype.

    Sources:
      Sales: Census SUSB 2013, 20-99 FTE, Professional services, national avg
             = $12,747,313.81 (Per City CODB tab, 20251213_Seattle Metro CODB comps)
      COGS:  IRS Returns Active Corps 2018, non-labor share, professional = 22.4%
      FTE / sqft / electricity: EDai Metro CODB model spec
    """
    return ProjectArchetype(
        name                   = "office",
        fte_count              = 50,
        sales                  = 12_747_314.0,
        cogs_share             = 0.224,   # non-labor COGS, professional services
        sqft                   = 10_000,
        electricity_kw         = 40,
        electricity_kwh_monthly = 10_000,
        water_volume_tier      = "office_tier",   # 20 CCF/month ≈ 15,000 gal
        occupation_mix         = {
            "General and Operations Managers":    1,
            "Human Resources Managers":           1,
            "Buyers and Purchasing Agents":       3,
            "Claims Adjusters, Examiners, and Investigators": 5,
            "Accountants and Auditors":           6,
            "Financial and Investment Analysts":  3,
            "Database Administrators":            2,
            "Computer User Support Specialists":  2,
            "Sales Representatives of Services, Except Advertising, Insurance, Financial Services, and Travel": 5,
            "Bookkeeping, Accounting, and Auditing Clerks":  4,
            "Customer Service Representatives":   8,
            "First-Line Supervisors of Office and Administrative Support Workers": 2,
            "Office Clerks, General":             8,
        },
        federal_ss_medicare_futa = 0.059,
        discretionary_benefits   = 0.184,
        federal_tax_rate         = 0.21,  # spec; Excel uses Penn Wharton 21.22%
        cap_rate                 = 0.06,
    )


def _build_manufacturing_archetype() -> ProjectArchetype:
    """50-person manufacturing archetype.

    Sales: Census SUSB 2013, 20-99 FTE, Manufacturing national avg
           = $33,668,321.66
    COGS:  IRS Returns Active Corps 2018, non-labor share, manufacturing = 61.5%
    """
    return ProjectArchetype(
        name                   = "manufacturing",
        fte_count              = 50,
        sales                  = 33_668_322.0,
        cogs_share             = 0.615,   # non-labor COGS, manufacturing
        sqft                   = 35_000,
        electricity_kw         = 75,
        electricity_kwh_monthly = 50_000,
        water_volume_tier      = "manuf_tier",    # 1337 CCF/month ≈ 100,000 gal
        occupation_mix         = {
            "Industrial Production Managers":     1,
            "Industrial Engineers":               1,
            "Maintenance Workers, Machinery":     2,
            "First-Line Supervisors of Production and Operating Workers": 2,
            "Miscellaneous Assemblers and Fabricators": 12,
            "Computer Numerically Controlled Tool Operators": 12,
            "Machinists":                         4,
            "Tool and Die Makers":                2,
            "Welders, Cutters, Solderers, and Brazers": 4,
            "Inspectors, Testers, Sorters, Samplers, and Weighers": 3,
            "Laborers and Freight, Stock, and Material Movers, Hand": 7,
        },
        federal_ss_medicare_futa = 0.059,
        discretionary_benefits   = 0.184,
        federal_tax_rate         = 0.21,  # spec; Excel uses Penn Wharton 15.41%
        cap_rate                 = 0.06,
    )


def _build_distribution_archetype() -> ProjectArchetype:
    """25-person distribution/warehousing archetype.

    Sales: Census SUSB 2013, 20-99 FTE, T&W national avg = $9,876,518.98
    COGS:  IRS Returns Active Corps 2018, non-labor share, T&W = 30.4%
    """
    return ProjectArchetype(
        name                   = "distribution",
        fte_count              = 25,
        sales                  = 9_876_519.0,
        cogs_share             = 0.304,   # non-labor COGS, transportation & warehousing
        sqft                   = 80_000,
        electricity_kw         = 1_000,
        electricity_kwh_monthly = 200_000,
        water_volume_tier      = "office_tier",   # smaller volume; 20 CCF tier
        occupation_mix         = {
            "Transportation, Storage, and Distribution Managers": 1,
            "Shipping, Receiving, and Inventory Clerks":          2,
            "Stockers and Order Fillers":                         2,
            "First-Line Supervisors of Transportation and Material Moving Workers, Except Aircraft Cargo Handling Supervisors": 2,
            "Heavy and Tractor-Trailer Truck Drivers":            2,
            "Industrial Truck and Tractor Operators":             3,
            "Laborers and Freight, Stock, and Material Movers, Hand": 6,
            "Packers and Packagers, Hand":                        6,
            "Receptionists and Information Clerks":               1,
        },
        federal_ss_medicare_futa = 0.059,
        discretionary_benefits   = 0.184,
        federal_tax_rate         = 0.21,  # spec; Excel uses Penn Wharton 22.19%
        cap_rate                 = 0.06,
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, str):
        if v in ('#N/A', 'N/A', '', 'None'):
            return None
        v = v.replace(',', '')
    try:
        f = float(v)
        return None if f != f else f   # NaN → None
    except (TypeError, ValueError):
        return None


def _add_optional(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Sum two optional floats; return None only if both are None."""
    if a is None and b is None:
        return None
    return (a or 0.0) + (b or 0.0)


def _derive_state(
    city_state: str,
    abb_to_name: dict[str, str],
    name_to_abb: dict[str, str],
) -> tuple[str, str]:
    """Extract (state_full, state_abb) from "City, State Name" string."""
    parts = city_state.rsplit(",", 1)
    if len(parts) == 2:
        state_raw = parts[1].strip()
        state_full = state_raw
        state_abb  = name_to_abb.get(state_raw.lower(), "")
        if not state_abb:
            # Try matching as abbreviation
            if state_raw.upper() in abb_to_name:
                state_abb  = state_raw.upper()
                state_full = abb_to_name[state_abb]
        return state_full, state_abb
    return "", ""
