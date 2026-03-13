"""
metro_codb/codb_engine.py
11-step P&L calculation engine for the Metro CODB model.

Mirrors the logic in Dynamic Metro CODB_20230609_Copy_vTS.xlsx / Outputs tab
and the benchmark definitions in Per City CODB tab of
20251213_Seattle Metro CODB comps.xlsm.

Step-by-step:
  1. Sales            — fixed Census SUSB national avg per archetype
  2. Salaries         — BLS OEWS metro wages × occupation headcount mix
  3. Benefits         — 5.9% fed fixed + 18.4% discretionary (of salary)
                        + workers comp (rate × salary)
                        + SUI (flat per FTE × FTE count)
                        + health premiums (flat per FTE × FTE count)
  4. Real estate      — office/industrial rent × sqft
                        + property tax on proxy building value
  5. Utilities        — electricity (EIA $/kWh × monthly kWh × 12)
                        + water/sewer (monthly charge × 12)
  6. COGS             — non-labor share × sales (IRS Returns 2018)
  7. Total locally varying costs = Salaries + Benefits + RE + Utilities
  8. Pre-tax income   = Sales − Total Locally Varying Costs − COGS
  9. Federal tax      = pre-tax income × 21% (spec)
 10. State/local tax  = pre-tax income × EY/COST effective rate
 11. After-tax margin = (Pre-tax − Fed tax − S/L tax) / Sales
"""

from __future__ import annotations
import logging
from typing import Optional

from .models import MetroRates, ProjectArchetype, PnLResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_pnl(
    metro_rates: MetroRates,
    archetype: ProjectArchetype,
) -> PnLResult:
    """Compute full P&L for one metro × archetype combination.

    Parameters
    ----------
    metro_rates : MetroRates
        All locally-varying rates for the target metro.
    archetype : ProjectArchetype
        Fixed parameters for the chosen archetype.

    Returns
    -------
    PnLResult
        Populated result including after_tax_margin and cost_breakdown.
    """
    result = PnLResult(metro=metro_rates.metro_name, archetype=archetype.name)
    fallbacks: dict = {}

    # ------------------------------------------------------------------
    # Step 1: Sales
    # ------------------------------------------------------------------
    result.sales = archetype.sales

    # ------------------------------------------------------------------
    # Step 2: Salaries
    # ------------------------------------------------------------------
    total_salaries = 0.0
    for occupation, headcount in archetype.occupation_mix.items():
        wage = metro_rates.wages_by_occupation.get(occupation)
        source = metro_rates.wages_source.get(occupation, "MISSING")

        if wage is None:
            # Missing wage data — log and skip this occupation's contribution
            logger.warning(
                "Metro '%s': no wage for occupation '%s' (headcount=%d) — "
                "contribution set to $0",
                metro_rates.metro_name, occupation, headcount,
            )
            fallbacks[f"wages.{occupation}"] = "MISSING"
            continue

        if source != "MSA":
            fallbacks[f"wages.{occupation}"] = source

        total_salaries += wage * headcount

    result.salaries = total_salaries

    # ------------------------------------------------------------------
    # Step 3: Benefits
    # ------------------------------------------------------------------

    # 3a. Federal fixed benefits (SS + Medicare + FUTA) — 5.9% of salary
    result.benefits_federal_fixed = total_salaries * archetype.federal_ss_medicare_futa

    # 3b. Discretionary benefits (paid leave, insurance, retirement) — 18.4%
    result.benefits_discretionary = total_salaries * archetype.discretionary_benefits

    # 3c. Workers compensation — rate × total salary payroll
    wc_rate = metro_rates.workers_comp_rate
    if wc_rate is None:
        logger.warning("Metro '%s': workers comp rate missing", metro_rates.metro_name)
        fallbacks["workers_comp"] = "MISSING"
        wc_rate = 0.0
    result.benefits_workers_comp = total_salaries * wc_rate

    # 3d. State unemployment insurance — flat per FTE
    sui_per_fte = metro_rates.sui_annual_per_fte
    if sui_per_fte is None:
        logger.warning("Metro '%s': SUI per FTE missing", metro_rates.metro_name)
        fallbacks["sui"] = "MISSING"
        sui_per_fte = 0.0
    result.benefits_sui = sui_per_fte * archetype.fte_count

    # 3e. Employer health premiums — flat per FTE
    health = metro_rates.health_premium_per_fte
    if health is None:
        logger.warning("Metro '%s': health premium missing", metro_rates.metro_name)
        fallbacks["health_premium"] = "MISSING"
        health = 0.0
    result.benefits_health = health * archetype.fte_count

    result.benefits_total = (
        result.benefits_federal_fixed
        + result.benefits_discretionary
        + result.benefits_workers_comp
        + result.benefits_sui
        + result.benefits_health
    )

    # ------------------------------------------------------------------
    # Step 4: Real estate
    # ------------------------------------------------------------------

    # Rent: use office_rent for office archetype, industrial_rent for manuf/dist
    if archetype.name == "office":
        rent_psf = metro_rates.office_rent_sqft
        rent_source = metro_rates.office_rent_source
        if rent_psf is None:
            fallbacks["office_rent"] = "MISSING"
            logger.warning("Metro '%s': office rent missing", metro_rates.metro_name)
            rent_psf = 0.0
    else:
        rent_psf = metro_rates.industrial_rent_sqft
        rent_source = metro_rates.industrial_rent_source
        if rent_psf is None:
            fallbacks["industrial_rent"] = "MISSING"
            logger.warning("Metro '%s': industrial rent missing", metro_rates.metro_name)
            rent_psf = 0.0

    result.office_or_industrial_rent = rent_psf * archetype.sqft

    # Property tax: apply to proxy building value = annual_rent / cap_rate
    prop_tax_rate = metro_rates.property_tax_rate
    if prop_tax_rate is None:
        logger.warning("Metro '%s': property tax rate missing", metro_rates.metro_name)
        fallbacks["property_tax"] = "MISSING"
        prop_tax_rate = 0.0

    proxy_building_value = (result.office_or_industrial_rent / archetype.cap_rate
                            if archetype.cap_rate > 0 else 0.0)
    result.property_tax = proxy_building_value * prop_tax_rate

    result.real_estate = result.office_or_industrial_rent + result.property_tax

    # ------------------------------------------------------------------
    # Step 5: Utilities
    # ------------------------------------------------------------------

    # Electricity: EIA $/kWh × monthly kWh × 12 months
    # Office uses commercial rate; manufacturing/distribution use industrial rate
    if archetype.name == "office":
        elec_rate = metro_rates.electricity_rate_commercial
        elec_source = metro_rates.electricity_rate_commercial_source
        if elec_rate is None:
            fallbacks["electricity_commercial"] = "MISSING"
            logger.warning("Metro '%s': commercial electricity rate missing", metro_rates.metro_name)
            elec_rate = 0.0
    else:
        elec_rate = metro_rates.electricity_rate_industrial
        elec_source = metro_rates.electricity_rate_industrial_source
        if elec_rate is None:
            fallbacks["electricity_industrial"] = "MISSING"
            logger.warning("Metro '%s': industrial electricity rate missing", metro_rates.metro_name)
            elec_rate = 0.0

    result.electricity = elec_rate * archetype.electricity_kwh_monthly * 12

    # Water/sewer: monthly charge × 12 months
    # Office / distribution use 20-CCF tier; manufacturing uses 1337-CCF tier
    if archetype.water_volume_tier == "manuf_tier":
        ws_monthly = metro_rates.water_sewer_monthly_manuf
    else:
        ws_monthly = metro_rates.water_sewer_monthly_office

    if ws_monthly is None:
        fallbacks["water_sewer"] = "MISSING"
        logger.warning("Metro '%s': water/sewer monthly missing", metro_rates.metro_name)
        ws_monthly = 0.0

    result.water_sewer = ws_monthly * 12
    result.utilities = result.electricity + result.water_sewer

    # ------------------------------------------------------------------
    # Step 6: COGS (non-labor)
    # ------------------------------------------------------------------
    result.cogs = archetype.cogs_share * result.sales

    # ------------------------------------------------------------------
    # Step 7: Total locally varying costs
    # ------------------------------------------------------------------
    result.total_local_varying_costs = (
        result.salaries
        + result.benefits_total
        + result.real_estate
        + result.utilities
    )

    result.total_costs = result.total_local_varying_costs + result.cogs

    # ------------------------------------------------------------------
    # Step 8: Pre-tax income
    # ------------------------------------------------------------------
    result.pretax_income = result.sales - result.total_costs

    # ------------------------------------------------------------------
    # Step 9: Federal income tax  (21% flat — spec)
    # Note: Per City CODB uses Penn Wharton Budget Model industry-specific
    # estimates (office=21.22%, manuf=15.41%, dist=22.19%). The spec
    # specifies 21% flat across all archetypes for simplicity.
    # ------------------------------------------------------------------
    result.federal_tax = max(0.0, result.pretax_income) * archetype.federal_tax_rate

    # ------------------------------------------------------------------
    # Step 10: State & local tax
    # ------------------------------------------------------------------
    sl_rate = metro_rates.state_local_tax_rate
    if sl_rate is None:
        fallbacks["state_local_tax"] = "MISSING"
        logger.warning("Metro '%s': state/local tax rate missing", metro_rates.metro_name)
        sl_rate = 0.0

    result.state_local_tax = max(0.0, result.pretax_income) * sl_rate
    result.total_taxes = result.federal_tax + result.state_local_tax

    # ------------------------------------------------------------------
    # Step 11: After-tax margin
    # ------------------------------------------------------------------
    result.after_tax_income = result.pretax_income - result.total_taxes
    result.after_tax_margin = (result.after_tax_income / result.sales
                               if result.sales > 0 else 0.0)

    result.fallbacks_used = fallbacks

    # ------------------------------------------------------------------
    # Cost breakdown (for reporting)
    # ------------------------------------------------------------------
    result.cost_breakdown = {
        "salaries":              result.salaries,
        "benefits_federal":      result.benefits_federal_fixed,
        "benefits_discretionary": result.benefits_discretionary,
        "benefits_workers_comp": result.benefits_workers_comp,
        "benefits_sui":          result.benefits_sui,
        "benefits_health":       result.benefits_health,
        "rent":                  result.office_or_industrial_rent,
        "property_tax":          result.property_tax,
        "electricity":           result.electricity,
        "water_sewer":           result.water_sewer,
        "cogs":                  result.cogs,
        "federal_tax":           result.federal_tax,
        "state_local_tax":       result.state_local_tax,
    }

    return result


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def compute_all_metros(
    metro_rates_list: list[MetroRates],
    archetype: ProjectArchetype,
    sort_by_margin: bool = True,
) -> list[PnLResult]:
    """Run compute_pnl for every metro in metro_rates_list.

    Parameters
    ----------
    metro_rates_list : list[MetroRates]
    archetype : ProjectArchetype
    sort_by_margin : bool
        If True, return results sorted descending by after_tax_margin.

    Returns
    -------
    list[PnLResult]
    """
    results = [compute_pnl(mr, archetype) for mr in metro_rates_list]
    if sort_by_margin:
        results.sort(key=lambda r: r.after_tax_margin, reverse=True)
    return results
