"""
Data models for the Economic Impact engine.

Three top-level structures:
  RIMSMultiplierSet      Five Type II tables for one geography
  ProjectEconomicInputs  All user inputs for a single project
  EconomicImpactResult   Full output
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# RIMS II multiplier data for one state / geography
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RIMSMultiplierSet:
    """Five RIMS II Type II tables for a single geography.

    Tables dict keys (matching JSON file layout):
        "2-1_Output"   → Final-demand output multipliers  (22 aggregate sectors × 64 industries)
        "2-2_Earnings" → Final-demand earnings multipliers
        "2-3_Employ"   → Final-demand employment multipliers
        "2-4_ValAdd"   → Final-demand value-added multipliers
        "2-5_TotMult"  → Total multipliers (64 industries × 6 columns)

    Each table entry is the raw parsed dict from the JSON file:
        matrix tables:  {"meta": {...}, "industry_codes": [...], "industry_names": [...], "rows": [...]}
        TotMult table:  {"meta": {...}, "column_headers": [...], "rows": [...]}

    Each TotMult row has:
        industry_code, industry_name,
        fd_output, fd_earnings, fd_employment, fd_value_added,
        de_earnings, de_employment
    """

    state: str               # e.g. "VA", "NC"
    tables: Dict[str, Any]   # table_key → parsed table dict
    vintage: str             # e.g. "2012 I-O / 2018 Regional Data"
    is_placeholder: bool = False  # True when Virginia fallback is used for another state


# ─────────────────────────────────────────────────────────────────────────────
# User inputs for a single project
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProjectEconomicInputs:
    """All inputs needed to compute economic impact for one project.

    Args:
        state:               Full state name, e.g. "Virginia", "Texas"
        county:              County or locality name (informational; used for logging)
        sector:              User-facing sector label — matched against crosswalk irs_sector.
                             Examples: "Telecommunications", "Professional, scientific, and
                             technical services", "Manufacturing"
        direct_jobs:         Number of FTE jobs the project creates directly.
        direct_earnings:     Total annual payroll for direct jobs (dollars).
                             Used to derive estimated direct sales via SUSB payroll/sales ratio.
        capex:               Total capital expenditure for construction phase (dollars).
        discount_rate:       Discount rate for NPV calculations (default 5 %).
        inflation_rate:      Long-run inflation rate (default 3 %).
        construction_splits: Share of capex allocated to each cost category.
                             Defaults: materials 40 %, soft costs 10 %, labor 50 %.
        capture_rates:       Fraction of each capex category retained in the local economy.
                             Defaults per whitepaper:
                               materials  → 39.8 % sourced locally × 80 % captured = 31.84 %
                               soft_costs → 100 %
                               labor_wages    → 100 %
                               labor_benefits → 35 %
    """

    state: str
    county: str
    sector: str
    direct_jobs: int
    direct_earnings: float       # annual payroll, $
    capex: float                 # total construction capex, $

    discount_rate: float = 0.05
    inflation_rate: float = 0.03

    construction_splits: Dict[str, float] = field(default_factory=lambda: {
        "materials":   0.40,
        "soft_costs":  0.10,
        "labor":       0.50,
    })

    # Within the "labor" split: wages are 70 %, benefits 30 %
    labor_wage_share:    float = 0.70
    labor_benefit_share: float = 0.30

    capture_rates: Dict[str, float] = field(default_factory=lambda: {
        "materials":      0.398 * 0.80,   # 39.8% locally sourced × 80% captured = 31.84%
        "soft_costs":     1.00,
        "labor_wages":    1.00,
        "labor_benefits": 0.35,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Full output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OperationsImpact:
    """Economic impact from ongoing operations of the project."""

    # Direct inputs (as derived/provided)
    direct_jobs: int
    direct_earnings: float       # $
    direct_sales_estimated: float  # $ — derived from SUSB payroll/sales ratio

    # Multipliers used
    bea_industry_code: str
    bea_industry_name: str
    de_employment_mult: float    # direct-effect employment multiplier
    de_earnings_mult:   float    # direct-effect earnings multiplier
    fd_output_mult:     float    # final-demand output multiplier
    fd_earnings_mult:   float    # final-demand earnings multiplier
    fd_employment_mult: float    # final-demand employment multiplier
    fd_value_added_mult: float   # final-demand value-added multiplier

    # Total impacts
    total_jobs:        float     # direct_jobs × de_employment_mult
    total_earnings:    float     # $ — direct_earnings × de_earnings_mult
    total_output:      float     # $ — direct_sales × fd_output_mult
    total_value_added: float     # $ — direct_sales × fd_value_added_mult


@dataclass
class ConstructionImpact:
    """Economic impact from the capital expenditure / construction phase."""

    capex: float

    # Captured amounts after splits and capture rates
    materials_captured:      float   # $
    soft_costs_captured:     float   # $
    labor_wages_captured:    float   # $
    labor_benefits_captured: float   # $
    total_captured:          float   # $

    # Construction multipliers (RIMS II "Construction" row)
    bea_industry_code:  str          # "7.0" for Construction
    bea_industry_name:  str
    fd_output_mult:     float
    fd_earnings_mult:   float
    fd_employment_mult: float
    fd_value_added_mult: float

    # Total construction-phase impacts
    total_jobs:        float     # total_captured / 1e6 × fd_employment_mult (jobs per $M)
    total_earnings:    float     # $ — total_captured × fd_earnings_mult
    total_output:      float     # $ — total_captured × fd_output_mult
    total_value_added: float     # $ — total_captured × fd_value_added_mult


@dataclass
class SectorBreakdownRow:
    """Impact in one BEA aggregate sector (summed across direct + indirect + induced)."""

    sector_code: str
    sector_name: str
    output:       float   # $
    earnings:     float   # $
    employment:   float   # jobs
    value_added:  float   # $


@dataclass
class EconomicImpactResult:
    """Full economic impact output for a project.

    Summary totals combine operations + construction phases.
    """

    # Sub-results
    operations:   OperationsImpact
    construction: ConstructionImpact

    # Combined totals
    total_jobs:        float
    total_earnings:    float    # $
    total_output:      float    # $
    total_value_added: float    # $

    # Sector-by-sector breakdown (operations phase)
    sector_breakdown: List[SectorBreakdownRow]

    # Data quality flags
    placeholder_multipliers_used: bool   # True when Virginia fallback was applied
    placeholder_state_requested:  Optional[str]  # state that triggered the fallback
    warnings: List[str]
