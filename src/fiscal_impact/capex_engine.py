"""
capex_engine.py — Capital expenditure schedule and taxable property calculations.

Computes, for each year of the analysis:
  - Assessed real property value (land + improvements)
  - Assessed personal property value (M&T, TPP, inventory)
  - Total taxable property (real + personal)

Uses the capex splits extracted from the Excel model and the depreciation
schedule in ProjectInputs.

Note: Construction labor is a COST, not an assessable asset.
Only physical assets (land, building improvements, personal property)
are subject to property tax assessment.
"""

from __future__ import annotations
from typing import Dict, List, Tuple

from .models import ProjectInputs, LocationRates


# Standard capex category tags used for lookup
_LAND_TAGS      = ("land",)
_MATERIAL_TAGS  = ("construction material", "material")
_LABOR_TAGS     = ("construction labor", "labor")   # excluded from property tax
_MT_TAGS        = ("machinery", "m&t", "equipment")
_TPP_TAGS       = ("tangible personal", "fixture", "tpp")
_INVENTORY_TAGS = ("inventory",)


def _match_cat(category: str, tags: tuple) -> bool:
    c = category.lower()
    return any(t in c for t in tags)


def compute_capex_property_base(
    capex_total: float,
    capex_splits: Dict[str, float],
    project_type: str = "commercial",
) -> Dict[str, float]:
    """
    Break the total capex into taxable real and personal property components.

    Returns a dict with keys:
        land              — assessable land value
        improvements      — assessable building improvement value (materials only, not labor)
        real_property     — land + improvements
        machinery         — M&T value
        tpp               — tangible personal property (fixtures, equipment)
        inventory         — inventory value
        personal_property — M&T + TPP + inventory
        total_assessable  — real + personal property subject to tax
        construction_labor — labor cost (NOT assessable, for reference)
    """
    land          = 0.0
    improvements  = 0.0
    labor_cost    = 0.0
    machinery     = 0.0
    tpp           = 0.0
    inventory     = 0.0

    for category, share in capex_splits.items():
        if share is None:
            continue
        amount = capex_total * share
        cat    = category.lower()

        if _match_cat(cat, _LAND_TAGS):
            land += amount
        elif _match_cat(cat, _MATERIAL_TAGS):
            improvements += amount
        elif _match_cat(cat, _LABOR_TAGS):
            labor_cost += amount      # not assessable
        elif _match_cat(cat, _TPP_TAGS):            # check TPP before M&T to avoid "equipment" in TPP name matching M&T
            tpp += amount
        elif _match_cat(cat, _MT_TAGS):
            machinery += amount
        elif _match_cat(cat, _INVENTORY_TAGS):
            inventory += amount
        # else: unclassified, ignore

    real_prop     = land + improvements
    personal_prop = machinery + tpp + inventory
    total         = real_prop + personal_prop

    return {
        "land":               land,
        "improvements":       improvements,
        "real_property":      real_prop,
        "machinery":          machinery,
        "tpp":                tpp,
        "inventory":          inventory,
        "personal_property":  personal_prop,
        "total_assessable":   total,
        "construction_labor": labor_cost,
    }


def annual_taxable_property(
    base: Dict[str, float],
    year: int,
    depreciation_schedule: Dict[int, float],
) -> Tuple[float, float, float]:
    """
    Return (real_property_value, personal_property_value, total_taxable_value)
    for the given project year, after applying the depreciation schedule.

    Real property typically depreciates more slowly (or holds value);
    personal property (M&T, TPP) depreciates faster.

    Implementation: applies the session-brief depreciation schedule uniformly
    to both real and personal property.
    """
    depr = depreciation_schedule.get(year, 0.80)   # default: 80% after year 5+

    real     = base["real_property"]    * depr
    personal = base["personal_property"] * depr

    return real, personal, real + personal


def property_tax_schedule(
    inputs: ProjectInputs,
    rates: LocationRates,
    capex_splits: Dict[str, float],
) -> List[float]:
    """
    Compute annual LOCAL property tax revenue for the analysis period.

    Uses the local property tax rate (rates.property_tax_rate) and the
    depreciation schedule to compute assessed value each year.
    """
    base = compute_capex_property_base(
        inputs.capital_investment,
        capex_splits,
        inputs.project_type,
    )

    prop_tax_rate = rates.property_tax_rate
    revenues: List[float] = []

    for yr in range(1, inputs.analysis_years + 1):
        _, _, total_taxable = annual_taxable_property(
            base,
            yr,
            inputs.depreciation_schedule,
        )
        revenues.append(total_taxable * prop_tax_rate)

    return revenues


def construction_materials_annual(
    inputs: ProjectInputs,
    capex_splits: Dict[str, float],
) -> List[float]:
    """
    Annual construction material purchases, spread evenly over construction_years.
    These are taxable under sales tax.

    After construction_years, ongoing M&T replacement purchases continue
    (amortized over equipment useful life).
    """
    mat_share  = 0.0
    mt_share   = 0.0
    bldg_life  = 40   # years for real property depreciation
    mt_life    = 5    # years for M&T depreciation

    for category, share in capex_splits.items():
        if share is None:
            continue
        cat = category.lower()
        if _match_cat(cat, _MATERIAL_TAGS):
            mat_share += share
        elif _match_cat(cat, _TPP_TAGS):
            pass   # TPP (fixtures, equipment) tracked separately; not a construction material
        elif _match_cat(cat, _MT_TAGS):
            mt_share += share

    total_materials = inputs.capital_investment * mat_share
    total_mt        = inputs.capital_investment * mt_share

    annual_mat_during_construction = (
        total_materials / inputs.construction_years
        if inputs.construction_years > 0 else 0.0
    )
    annual_mt_replacement = total_mt / mt_life if mt_life > 0 else 0.0
    annual_bldg_replacement = total_materials / bldg_life if bldg_life > 0 else 0.0

    result: List[float] = []
    for yr in range(1, inputs.analysis_years + 1):
        if yr <= inputs.construction_years:
            # Active construction: one-time material purchases
            amt = annual_mat_during_construction + annual_bldg_replacement + annual_mt_replacement
        else:
            # Post-construction: ongoing replacement only
            amt = annual_bldg_replacement + annual_mt_replacement
        result.append(amt)

    return result
