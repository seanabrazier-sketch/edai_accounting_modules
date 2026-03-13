"""
metro_codb/models.py
Data structures for the Metro Cost of Doing Business engine.

Three dataclasses:
  MetroRates       — one record per metro, all locally varying rates
  ProjectArchetype — fixed parameters per archetype (office/manufacturing/distribution)
  PnLResult        — output per metro × archetype
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# MetroRates — all locally varying inputs for a single metro
# ---------------------------------------------------------------------------

@dataclass
class MetroRates:
    """One record per metro containing all locally-varying cost rates.

    Wages are stored as a dict mapping detailed occupation name → annual
    median wage (from BLS OEWS).  The fallback chain is:
        1. MSA-level OEWS 2022 (primary)
        2. State-level OEWS 2022
        3. National OEWS 2022
    Each wage entry also records which level was used via wages_source.

    All monetary values are in USD per year unless noted.
    Rates (workers_comp_rate, sui_annual_per_fte, etc.) are per-dollar of
    payroll or flat per-FTE as described in the field docstring.
    """

    # ---- Identity --------------------------------------------------------
    metro_name: str                        # e.g. "Seattle, Washington"
    emsi_area: str                         # BLS CBSA label
    state: str                             # Full state name
    state_abbrev: str                      # Two-letter abbreviation

    # ---- Wages -----------------------------------------------------------
    # detailed occupation → annual median wage (USD)
    wages_by_occupation: dict = field(default_factory=dict)
    # detailed occupation → data source tier ("MSA" | "State" | "National")
    wages_source: dict = field(default_factory=dict)

    # ---- Benefits (locally varying) ------------------------------------
    # Oregon 2024 workers comp index rate (per $1 of payroll, i.e. rate/100)
    workers_comp_rate: Optional[float] = None
    workers_comp_source: str = ""

    # SUI annual cost per FTE (USD) — computed as taxable_wage × max_rate
    sui_annual_per_fte: Optional[float] = None
    sui_source: str = ""

    # Employer contribution for family health coverage, annual per FTE (USD)
    health_premium_per_fte: Optional[float] = None
    health_premium_source: str = ""

    # ---- Real estate -----------------------------------------------------
    # Office rent $/sqft/year (CommercialEdge/CoStar blended Class A, 2023)
    office_rent_sqft: Optional[float] = None
    office_rent_source: str = ""

    # Industrial net rent $/sqft/year (CommercialEdge 2023)
    industrial_rent_sqft: Optional[float] = None
    industrial_rent_source: str = ""

    # Commercial property tax rate (Lincoln Institute 2019, largest city
    # in state; applied to proxy building value)
    property_tax_rate: Optional[float] = None
    property_tax_source: str = ""

    # ---- Utilities — electricity ----------------------------------------
    # EIA $/kWh commercial rate (annual avg, from Utility rates MSA pivot)
    electricity_rate_commercial: Optional[float] = None
    electricity_rate_commercial_source: str = ""

    # EIA $/kWh industrial rate
    electricity_rate_industrial: Optional[float] = None
    electricity_rate_industrial_source: str = ""

    # ---- Utilities — water/sewer ----------------------------------------
    # Total monthly water + sewer charge for ~20 CCF (≈15,000 gal; office)
    water_sewer_monthly_office: Optional[float] = None
    # Total monthly water + sewer charge for ~1337 CCF (manufacturing)
    water_sewer_monthly_manuf: Optional[float] = None
    water_sewer_source: str = ""

    # ---- Taxes ----------------------------------------------------------
    # EY/COST FY2022 total effective state & local tax rate (fraction)
    state_local_tax_rate: Optional[float] = None
    state_local_tax_source: str = ""


# ---------------------------------------------------------------------------
# ProjectArchetype — fixed parameters per archetype
# ---------------------------------------------------------------------------

@dataclass
class ProjectArchetype:
    """Fixed (non-locally-varying) parameters for one of the three archetypes.

    Sources:
      - Sales: Census SUSB national avg, 20-99 FTE size class, IRS 2013
               (from Per City CODB tab, 20251213_Seattle Metro CODB comps)
      - FTE / sqft: EDai Metro CODB model spec
      - COGS share: IRS Returns of Active Corporations 2018, non-labor share
      - Occupation mix: Dynamic Metro CODB Inputs tab standard headcount
    """

    name: str                            # "office" | "manufacturing" | "distribution"

    # ---- Scale -----------------------------------------------------------
    fte_count: int                       # Total headcount
    sales: float                         # Annual sales (USD) — national SUSB avg

    # ---- COGS ------------------------------------------------------------
    # Non-labor COGS as fraction of sales (IRS Returns 2018)
    # Office (professional): 22.4%  | Manufacturing: 61.5% | Distribution: 30.4%
    cogs_share: float

    # ---- Real estate -----------------------------------------------------
    sqft: int                            # Total square footage

    # ---- Electricity load profile ----------------------------------------
    electricity_kw: int                  # Peak demand (kW)
    electricity_kwh_monthly: int         # Monthly energy consumption (kWh)

    # ---- Water usage -----------------------------------------------------
    # "office" → 20 CCF/month (~15,000 gal)
    # "manufacturing" → 1337 CCF/month (~100,000 gal)
    # "distribution" → 20 CCF/month (same scale as office, fewer FTE)
    water_volume_tier: str               # "office_tier" | "manuf_tier"

    # ---- Occupation mix --------------------------------------------------
    # detailed occupation name → headcount
    occupation_mix: dict = field(default_factory=dict)

    # ---- Federal benefits (fixed, not locally varying) ------------------
    # BLS Table 1 ECEC rates applied to salary payroll
    federal_ss_medicare_futa: float = 0.059   # 5.9%
    discretionary_benefits: float = 0.184     # 18.4%

    # ---- Federal income tax -----------------------------------------------
    # Flat 21% per spec; Excel uses Penn Wharton estimates (noted in comments)
    federal_tax_rate: float = 0.21

    # ---- Real estate cap rate (for proxy building value) -----------------
    # Used to derive building value from rent: building_value = rent / cap_rate
    cap_rate: float = 0.06


# ---------------------------------------------------------------------------
# PnLResult — output per metro × archetype
# ---------------------------------------------------------------------------

@dataclass
class PnLResult:
    """Full P&L output for one metro × archetype combination."""

    metro: str
    archetype: str

    # ---- P&L line items (all USD, annual) --------------------------------
    sales: float = 0.0

    # Salaries
    salaries: float = 0.0

    # Benefits breakdown
    benefits_federal_fixed: float = 0.0   # SS + Medicare + FUTA (5.9%)
    benefits_discretionary: float = 0.0   # Paid leave, insurance, retirement (18.4%)
    benefits_workers_comp: float = 0.0    # State workers comp
    benefits_sui: float = 0.0             # State unemployment insurance
    benefits_health: float = 0.0          # Employer health premiums
    benefits_total: float = 0.0

    # Real estate
    office_or_industrial_rent: float = 0.0
    property_tax: float = 0.0
    real_estate: float = 0.0              # rent + property_tax

    # Utilities
    electricity: float = 0.0
    water_sewer: float = 0.0
    utilities: float = 0.0

    # COGS (non-labor)
    cogs: float = 0.0

    # Subtotals
    total_local_varying_costs: float = 0.0  # salaries + benefits + RE + util
    total_costs: float = 0.0               # local + COGS

    # Income
    pretax_income: float = 0.0

    # Taxes
    federal_tax: float = 0.0
    state_local_tax: float = 0.0
    total_taxes: float = 0.0

    # Bottom line
    after_tax_income: float = 0.0
    after_tax_margin: float = 0.0          # after_tax_income / sales

    # ---- Data quality flags ----------------------------------------------
    # Dict of field → fallback tier used (e.g. "wages.Accountants and Auditors" → "State")
    fallbacks_used: dict = field(default_factory=dict)

    # ---- Cost breakdown for ranking/reporting ---------------------------
    cost_breakdown: dict = field(default_factory=dict)
