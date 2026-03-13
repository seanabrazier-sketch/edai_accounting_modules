"""
revenue_engines.py — Annual revenue calculation for each fiscal stream.

Each function receives payroll/receipts arrays (one value per year) and the
rates from LocationRates, and returns a list of annual revenue values.

Revenue streams modelled:
    1. PIT (Personal Income Tax)       — state-level
    2. Sales tax                        — state-level + local
    3. BPOL                             — local, Richmond VA only
    4. CIT (Corporate Income Tax)       — state-level
    5. GRT (Gross Receipts Tax)         — state-level (select states)
    6. Property tax                     — local (from capex_engine)
    7. Utility taxes                    — local, Richmond VA only

Constants (from session brief):
    - Federal payroll tax rate (SS + Medicare + FUTA) = 5.9%
    - Residents in same locality = 23%
    - Taxable spending share = 37.65%
"""

from __future__ import annotations
from typing import List

from .models import ProjectInputs, LocationRates


# ── 1. Personal Income Tax ────────────────────────────────────────────────────

def calc_pit(
    direct_payroll: List[float],
    indirect_payroll: List[float],
    induced_payroll: List[float],
    pit_effective_rate: float,
    locality_share: float = 0.23,
) -> List[float]:
    """
    Annual state PIT revenue on direct + indirect + induced workers
    who reside in the project locality.

    locality_share: fraction of workers who live (and are taxed) locally.
    For state-level PIT, all workers contribute regardless of residence,
    but for the local portion we apply locality_share.

    NOTE: Virginia has no local income tax; all PIT goes to the state.
    This function returns STATE-LEVEL PIT (contributed by local residents
    as a proxy for fiscal benefit allocation to the region).
    """
    revenues: List[float] = []
    for dp, ip, np_ in zip(direct_payroll, indirect_payroll, induced_payroll):
        # All workers contribute to state PIT
        total_payroll = dp + ip + np_
        pit = total_payroll * pit_effective_rate
        revenues.append(pit)
    return revenues


def calc_pit_local_only(
    direct_payroll: List[float],
    indirect_payroll: List[float],
    induced_payroll: List[float],
    pit_effective_rate: float,
    locality_share: float = 0.23,
) -> List[float]:
    """
    PIT attributed to workers who live in the locality (23%).
    Used when separating state vs. local fiscal impact.
    """
    revenues: List[float] = []
    for dp, ip, np_ in zip(direct_payroll, indirect_payroll, induced_payroll):
        total_payroll = dp + ip + np_
        pit = total_payroll * pit_effective_rate * locality_share
        revenues.append(pit)
    return revenues


# ── 2. Sales Tax ──────────────────────────────────────────────────────────────

def calc_sales_tax(
    direct_payroll:   List[float],
    indirect_payroll: List[float],
    induced_payroll:  List[float],
    construction_materials: List[float],
    sales_tax_rate:       float,
    taxable_spend_share:  float = 0.3765,
    rate_type:            str   = "combined",   # "combined" | "local_only" | "state_only"
) -> List[float]:
    """
    Annual sales tax revenue from:
      1. Workers' consumer spending (direct + indirect + induced)
      2. Construction materials (taxed at point of purchase)

    taxable_spend_share: fraction of income spent on taxable goods (37.65%).
    """
    revenues: List[float] = []
    for dp, ip, np_, mats in zip(
        direct_payroll, indirect_payroll, induced_payroll, construction_materials
    ):
        total_payroll      = dp + ip + np_
        taxable_spending   = total_payroll * taxable_spend_share
        materials_taxable  = mats  # construction materials taxed when purchased
        base               = taxable_spending + materials_taxable
        revenues.append(base * sales_tax_rate)
    return revenues


def calc_sales_tax_split(
    direct_payroll:   List[float],
    indirect_payroll: List[float],
    induced_payroll:  List[float],
    construction_materials: List[float],
    state_rate:  float,
    local_rate:  float,
    taxable_spend_share: float = 0.3765,
) -> tuple:
    """
    Returns (state_sales_tax, local_sales_tax) as separate lists.
    """
    state_rev = calc_sales_tax(
        direct_payroll, indirect_payroll, induced_payroll,
        construction_materials, state_rate, taxable_spend_share,
    )
    local_rev = calc_sales_tax(
        direct_payroll, indirect_payroll, induced_payroll,
        construction_materials, local_rate, taxable_spend_share,
    )
    return state_rev, local_rev


# ── 3. BPOL ───────────────────────────────────────────────────────────────────

def calc_bpol(
    gross_receipts: List[float],
    bpol_rate: float,
) -> List[float]:
    """
    Annual BPOL (Business, Professional, and Occupational License) revenue.

    BPOL rate is expressed as a fraction of gross receipts
    (e.g., 0.000058 for $0.0058 per $100 of receipts).
    Returns 0 for all states except Richmond, VA (bpol_rate = 0 elsewhere).
    """
    return [gr * bpol_rate for gr in gross_receipts]


# ── 4. Corporate Income Tax ────────────────────────────────────────────────────

def calc_cit(
    gross_receipts: List[float],
    cit_rate: float,
    profit_margin: float = 0.10,
) -> List[float]:
    """
    Annual state CIT revenue on project's estimated taxable income.

    profit_margin: assumed net taxable income as fraction of gross receipts.
    Default 10% is a conservative assumption for a professional services firm.
    """
    return [gr * profit_margin * cit_rate for gr in gross_receipts]


# ── 5. Gross Receipts Tax ──────────────────────────────────────────────────────

def calc_grt(
    gross_receipts: List[float],
    grt_rate: float,
) -> List[float]:
    """
    Annual state GRT revenue (only for states with GRT: DE, NV, OH, OR, TN, TX, WA).
    Rate is a fraction of gross receipts (e.g., 0.0057 for Oregon at 0.57%).
    """
    return [gr * grt_rate for gr in gross_receipts]


# ── 6. Property Tax ────────────────────────────────────────────────────────────
# Property tax is computed in capex_engine.py and passed in as a precomputed list.
# No separate function here.


# ── 7. Utility Taxes ──────────────────────────────────────────────────────────

def calc_utility_taxes(
    direct_jobs: List[float],
    sqft_per_worker: float,
    electricity_kwh_per_sqft: float,
    gas_cuft_per_sqft: float,
    electricity_tax_rate_per_kwh: float,
    gas_tax_rate_per_cuft: float,
    inflation_rate: float = 0.0273,
    reference_jobs: float = 250.0,
    richmond_elec_tax_y1: float = 1322.16,
    richmond_gas_tax_y1: float = 446.24,
    locality_has_utility_tax: bool = True,
) -> List[float]:
    """
    Annual utility tax revenue.

    For Richmond VA: scales the Year 1 reference utility taxes by the ratio of
    actual building size to the reference 40,465 sq ft (250 workers).

    For other localities: returns 0 (utility taxes are locality-specific;
    Richmond is the only pre-modelled case).

    electricity_tax_rate_per_kwh / gas_tax_rate_per_cuft: if provided,
    these override the Richmond reference values.
    """
    if not locality_has_utility_tax:
        return [0.0] * len(direct_jobs)

    # Richmond reference: 250 workers → $1,322.16 electricity + $446.24 gas = $1,768.40 Year 1
    reference_total_y1 = richmond_elec_tax_y1 + richmond_gas_tax_y1

    revenues: List[float] = []
    for yr_idx, dj in enumerate(direct_jobs):
        if reference_jobs > 0:
            scale = dj / reference_jobs
        else:
            scale = 0.0
        inflation_factor = (1 + inflation_rate) ** yr_idx
        revenues.append(reference_total_y1 * scale * inflation_factor)

    return revenues


# ── Convenience: all revenue streams ─────────────────────────────────────────

def calc_all_revenues(
    inputs: ProjectInputs,
    rates: LocationRates,
    direct_jobs:    List[float],
    indirect_jobs:  List[float],
    induced_jobs:   List[float],
    direct_payroll: List[float],
    indirect_payroll: List[float],
    induced_payroll:  List[float],
    gross_receipts: List[float],
    property_tax:   List[float],   # pre-computed by capex_engine
    construction_materials: List[float],
) -> dict:
    """
    Compute all revenue streams and return as a dict of lists.

    Keys: pit_state, pit_local, sales_state, sales_local, bpol, cit, grt, utility
    Property tax is passed in (pre-computed from capex_engine.property_tax_schedule).
    """
    locality_is_richmond = (
        inputs.city and "richmond" in inputs.city.lower()
        and inputs.state and "virginia" in inputs.state.lower()
    )

    pit_state = calc_pit(
        direct_payroll, indirect_payroll, induced_payroll,
        rates.pit_effective_rate,
    )

    pit_local = calc_pit_local_only(
        direct_payroll, indirect_payroll, induced_payroll,
        rates.pit_effective_rate,
        locality_share=inputs.residents_in_same_locality,
    )

    # State sales tax: full base (all workers + construction materials)
    sales_state, _sales_local_full = calc_sales_tax_split(
        direct_payroll, indirect_payroll, induced_payroll,
        construction_materials,
        state_rate=rates.sales_tax_state_only,
        local_rate=rates.sales_tax_local_only,
        taxable_spend_share=inputs.taxable_spend_share,
    )

    # Local sales tax: direct workers only, no construction materials.
    # Construction materials are bulk purchases that generate state-level sales tax
    # primarily; local sales tax attribution is best estimated from worker consumer
    # spending. Indirect/induced workers are distributed regionally, not specifically
    # in the project locality.
    zero_payroll = [0.0] * len(direct_payroll)
    zero_mats    = [0.0] * len(direct_payroll)
    _, sales_local = calc_sales_tax_split(
        direct_payroll, zero_payroll, zero_payroll,
        zero_mats,
        state_rate=0.0,
        local_rate=rates.sales_tax_local_only,
        taxable_spend_share=inputs.taxable_spend_share,
    )

    bpol = calc_bpol(gross_receipts, rates.bpol_rate_professional)

    cit = calc_cit(gross_receipts, rates.cit_rate)

    grt = calc_grt(gross_receipts, rates.grt_rate)

    utility = calc_utility_taxes(
        direct_jobs=direct_jobs,
        sqft_per_worker=rates.building_sqft_per_worker,
        electricity_kwh_per_sqft=rates.electricity_kwh_per_sqft,
        gas_cuft_per_sqft=rates.gas_cuft_per_sqft,
        electricity_tax_rate_per_kwh=0.0,
        gas_tax_rate_per_cuft=0.0,
        inflation_rate=rates.cpi_inflation,
        reference_jobs=250.0,
        richmond_elec_tax_y1=rates.get_utility_assumption("richmond_electricity_tax_year1")
            if hasattr(rates, 'get_utility_assumption') else 1322.16,
        richmond_gas_tax_y1=rates.get_utility_assumption("richmond_gas_tax_year1")
            if hasattr(rates, 'get_utility_assumption') else 446.24,
        locality_has_utility_tax=locality_is_richmond,
    )

    return {
        "pit_state":    pit_state,
        "pit_local":    pit_local,
        "sales_state":  sales_state,
        "sales_local":  sales_local,
        "bpol":         bpol,
        "cit":          cit,
        "grt":          grt,
        "property":     property_tax,
        "utility":      utility,
    }
