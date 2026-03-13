"""
api/input_mappers.py — Translates AnalyzeRequest fields into each engine's
native input format.

Mapping tables
--------------
Archetype (lowercase) → capitalized form for Incentives engine
Archetype             → BEA/RIMS2 sector for Economic Impact engine
Archetype             → RIMS2/IRS sector for Fiscal Impact engine
Archetype             → project_type for Fiscal Impact engine
Archetype             → ScoringConfig weights for Location Scoring engine
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import AnalyzeRequest


# ─────────────────────────────────────────────────────────────────────────────
# Archetype → Incentives engine archetype (capitalized)
# ─────────────────────────────────────────────────────────────────────────────

_INCENTIVES_ARCHETYPE_MAP = {
    "office":        "Office",
    "manufacturing": "Manufacturing",
    "distribution":  "Distribution",
}


def map_archetype_to_incentives(archetype: str) -> str:
    """Return the capitalized archetype name expected by the Incentives engine."""
    return _INCENTIVES_ARCHETYPE_MAP.get(archetype.lower(), "Office")


# ─────────────────────────────────────────────────────────────────────────────
# Archetype → Economic Impact engine sector (BEA industry name)
# ─────────────────────────────────────────────────────────────────────────────

_ECONOMIC_SECTOR_MAP = {
    "office":        "Management of companies and enterprises",
    "manufacturing": "Machinery manufacturing",
    "distribution":  "Truck transportation",
}


def map_archetype_to_sector(archetype: str) -> str:
    """
    Map intake archetype to the BEA/RIMS2 sector string used by the
    Economic Impact engine.  The engine has an internal crosswalk that
    performs fuzzy-matching, so the name does not need to be exact.
    """
    return _ECONOMIC_SECTOR_MAP.get(archetype.lower(), "Management of companies and enterprises")


# ─────────────────────────────────────────────────────────────────────────────
# Archetype → Fiscal Impact engine fields
# ─────────────────────────────────────────────────────────────────────────────

_FISCAL_PROJECT_TYPE_MAP = {
    "office":        "commercial",
    "manufacturing": "industrial",
    "distribution":  "industrial",
}

_FISCAL_RIMS2_SECTOR_MAP = {
    "office":        "Management of companies and enterprises",
    "manufacturing": "Fabricated metal product manufacturing",
    "distribution":  "Truck transportation",
}

_FISCAL_IRS_SECTOR_MAP = {
    "office":        "Management of companies and enterprises",
    "manufacturing": "Manufacturing",
    "distribution":  "Transportation and warehousing",
}


def map_archetype_to_project_type(archetype: str) -> str:
    """Return the fiscal impact project_type ('commercial' | 'industrial')."""
    return _FISCAL_PROJECT_TYPE_MAP.get(archetype.lower(), "commercial")


def map_archetype_to_rims2_sector(archetype: str) -> str:
    """Return the RIMS2 sector string for the Fiscal Impact engine."""
    return _FISCAL_RIMS2_SECTOR_MAP.get(archetype.lower(), "Management of companies and enterprises")


def map_archetype_to_irs_sector(archetype: str) -> str:
    """Return the IRS sector string for the Fiscal Impact engine."""
    return _FISCAL_IRS_SECTOR_MAP.get(archetype.lower(), "Management of companies and enterprises")


# ─────────────────────────────────────────────────────────────────────────────
# Archetype → Location Scoring ScoringConfig
# ─────────────────────────────────────────────────────────────────────────────

# Category-level weight multipliers per archetype.
# All unlisted categories get a multiplier of 1.0 (baseline).
_ARCHETYPE_CATEGORY_WEIGHTS = {
    "manufacturing": {
        # Labor pool depth and quality
        "Industry makeup":    3.0,   # total jobs, manufacturing share
        "Education":          2.5,   # skilled-trades and STEM pipeline
        "Income":             1.5,   # wage competitiveness
        "Real estate":        2.5,   # affordable industrial/warehouse space
        "Unions":             0.5,   # prefer lower union prevalence
        "City population":    1.5,
        "MSA":                1.5,
        "Demographics":       1.5,
        # Lifestyle amenities matter less for factory sites
        "F&B":                0.3,
        "Flex work culture":  0.3,
        "Key retailers":      0.3,
        "Fitness":            0.5,
        "Hotel":              0.5,
        "Travel":             1.0,
        "Event industry":     0.3,
    },
    "office": {
        # Talent attraction and quality of life
        "Education":          3.0,   # bachelor's share, adult population
        "Demographics":       2.5,   # young professional pipeline (25-44)
        "Income":             2.0,   # purchasing power / talent wages
        "F&B":                2.0,   # restaurant scene — talent magnet
        "Flex work culture":  2.5,   # coworking density → innovation signal
        "Fitness":            1.5,   # wellness amenities
        "Key retailers":      1.5,   # urban amenity proxy
        "Travel":             2.0,   # airport connectivity for exec travel
        "Hotel":              1.5,   # business travel accommodation
        "Industry makeup":    2.0,   # existing knowledge-economy base
        "MSA":                2.0,   # metro market size
        "Real estate":        1.5,   # commercial office availability
        "Unions":             0.5,
        "Event industry":     0.8,
        "City population":    1.5,
    },
    "distribution": {
        # Logistics infrastructure and cost
        "MSA":                3.0,   # consumer market reach
        "Industry makeup":    2.0,   # logistics/transportation base
        "Real estate":        3.0,   # affordable warehouse/industrial RE
        "Travel":             2.5,   # airport proximity for air freight
        "City population":    2.0,   # labor pool for warehouse ops
        "Income":             1.5,   # workforce wage competitiveness
        "Education":          1.0,
        "Unions":             0.5,   # prefer lower union prevalence
        "Demographics":       1.0,
        # Lifestyle amenities minimal for distribution
        "F&B":                0.3,
        "Flex work culture":  0.2,
        "Key retailers":      0.3,
        "Fitness":            0.5,
        "Hotel":              0.5,
        "Event industry":     0.2,
    },
}


def get_default_weights_for_archetype(archetype: str):
    """
    Return a normalized ScoringConfig with archetype-appropriate variable weights.

    Each variable's weight = base_weight (1.0) × category_multiplier.
    ScoringConfig.normalize() is called so weights sum to 100.

    Falls back to equal weights if variable specs cannot be loaded.
    """
    from ..location_scoring.data_loader import get_variable_specs
    from ..location_scoring.models import ScoringConfig

    try:
        specs = get_variable_specs()
    except Exception:
        # Graceful fallback: equal weights
        return None   # run_scoring() with None → equal weights

    arch = archetype.lower()
    cat_multipliers = _ARCHETYPE_CATEGORY_WEIGHTS.get(arch, {})

    weights: dict = {}
    for spec in specs:
        multiplier = cat_multipliers.get(spec.category, 1.0)
        weights[spec.name] = spec.default_weight * multiplier

    config = ScoringConfig(weights=weights)
    return config.normalize()


# ─────────────────────────────────────────────────────────────────────────────
# Build engine-specific input dicts from AnalyzeRequest
# ─────────────────────────────────────────────────────────────────────────────

def build_incentives_input(request: "AnalyzeRequest"):
    """Build IncentivesInput from AnalyzeRequest."""
    from ..accounting.accounting_model import IncentivesInput
    return IncentivesInput(
        archetype=map_archetype_to_incentives(request.archetype),
        headcount=request.headcount,
        avg_wage=request.avg_wage,
        capex=request.capex,
        state=request.effective_state,
    )


def build_economic_inputs(request: "AnalyzeRequest"):
    """Build ProjectEconomicInputs from AnalyzeRequest."""
    from ..economic_impact.models import ProjectEconomicInputs
    return ProjectEconomicInputs(
        state=request.effective_state,
        county=request.effective_county,
        sector=map_archetype_to_sector(request.archetype),
        direct_jobs=request.headcount,
        direct_earnings=float(request.headcount) * request.avg_wage,
        capex=request.capex,
    )


def build_fiscal_inputs(request: "AnalyzeRequest") -> dict:
    """Build fiscal impact inputs dict from AnalyzeRequest."""
    return {
        "state":              request.effective_state,
        "city":               request.effective_county,
        "direct_jobs":        request.headcount,
        "average_salary":     request.avg_wage,
        "capital_investment": request.capex,
        "ramp_up_years":      3,
        "project_start_year": 2025,
        "analysis_years":     10,
        "project_type":       map_archetype_to_project_type(request.archetype),
        "discount_type":      "societal",
        "rims2_sector":       map_archetype_to_rims2_sector(request.archetype),
        "irs_sector":         map_archetype_to_irs_sector(request.archetype),
        "construction_years": 2,
    }
