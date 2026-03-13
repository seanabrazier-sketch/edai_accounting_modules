"""
fiscal_engine.py — Main orchestration engine for fiscal impact calculations.

9-step pipeline:
    1. Employment trajectory (direct, indirect, induced)
    2. Payroll trajectory
    3. Gross receipts estimation
    4. Personal income tax (state + local attribution)
    5. Sales tax (state + local)
    6. BPOL (Richmond VA only)
    7. CIT / GRT
    8. Property / capital taxes
    9. Utility taxes
   10. NPV / discounting / breakeven

Usage:
    from fiscal_impact.fiscal_engine import run_fiscal_impact

    ts, summary = run_fiscal_impact(inputs, rates, incentive_cost=0)
"""

from __future__ import annotations
from typing import Optional, Tuple

from .models import FiscalSummary, FiscalTimeSeries, LocationRates, ProjectInputs
from .employment import (
    calculate_employment_trajectory,
    calculate_payroll_trajectory,
    estimate_gross_receipts,
)
from .capex_engine import (
    property_tax_schedule,
    construction_materials_annual,
)
from .revenue_engines import calc_all_revenues
from .npv_engine import (
    breakeven_year,
    cumulative_sum,
    present_value,
)


def run_fiscal_impact(
    inputs: ProjectInputs,
    rates: LocationRates,
    incentive_cost: float = 0.0,
) -> Tuple[FiscalTimeSeries, FiscalSummary]:
    """
    Run the full 9-step fiscal impact calculation pipeline.

    Parameters
    ----------
    inputs        : ProjectInputs   — project parameters
    rates         : LocationRates   — tax rates for the project location
    incentive_cost: float           — PV of incentives offered (for breakeven calc)

    Returns
    -------
    (FiscalTimeSeries, FiscalSummary)
    """

    # ── Step 1: Employment trajectory ─────────────────────────────────────────
    direct_jobs, indirect_jobs, induced_jobs, total_jobs = (
        calculate_employment_trajectory(inputs, rates)
    )

    # ── Step 2: Payroll trajectory ─────────────────────────────────────────────
    direct_payroll, indirect_payroll, induced_payroll = calculate_payroll_trajectory(
        inputs, rates,
        direct_jobs, indirect_jobs, induced_jobs,
    )

    # ── Step 3: Gross receipts ─────────────────────────────────────────────────
    gross_receipts = estimate_gross_receipts(
        direct_payroll,
        rates.payroll_to_receipts_ratio,
    )

    # ── Step 4-5: Property tax (from capex engine) ─────────────────────────────
    capex_splits = rates.capex_splits or {}
    prop_tax = property_tax_schedule(inputs, rates, capex_splits)

    # ── Step 6: Construction materials (for sales tax base) ───────────────────
    constr_mats = construction_materials_annual(inputs, capex_splits)

    # ── Steps 4-9: All revenue streams ────────────────────────────────────────
    revenues = calc_all_revenues(
        inputs=inputs,
        rates=rates,
        direct_jobs=direct_jobs,
        indirect_jobs=indirect_jobs,
        induced_jobs=induced_jobs,
        direct_payroll=direct_payroll,
        indirect_payroll=indirect_payroll,
        induced_payroll=induced_payroll,
        gross_receipts=gross_receipts,
        property_tax=prop_tax,
        construction_materials=constr_mats,
    )

    # ── LOCAL revenue assembly ─────────────────────────────────────────────────
    # Local = local sales tax + local property tax + BPOL + utility taxes
    # (PIT and CIT/GRT are state-level revenues)
    rev_pit      = revenues["pit_state"]    # state PIT (all workers)
    rev_sales    = revenues["sales_local"]  # local sales tax portion
    rev_bpol     = revenues["bpol"]         # local BPOL (Richmond only)
    rev_cit      = revenues["cit"]          # state CIT
    rev_grt      = revenues["grt"]          # state GRT
    rev_property = revenues["property"]     # local property tax
    rev_utility  = revenues["utility"]      # local utility tax (Richmond only)

    # Total LOCAL revenues (property + local sales + BPOL + utility)
    total_local = [
        revenues["property"][i]
        + revenues["sales_local"][i]
        + revenues["bpol"][i]
        + revenues["utility"][i]
        for i in range(inputs.analysis_years)
    ]

    cumulative_local = cumulative_sum(total_local)

    # Calendar years
    calendar_years = [
        inputs.project_start_year + i
        for i in range(inputs.analysis_years)
    ]

    # ── Assemble FiscalTimeSeries ──────────────────────────────────────────────
    ts = FiscalTimeSeries(
        years=inputs.analysis_years,
        calendar_years=calendar_years,
        direct_jobs=direct_jobs,
        indirect_jobs=indirect_jobs,
        induced_jobs=induced_jobs,
        total_jobs=total_jobs,
        direct_payroll=direct_payroll,
        gross_receipts=gross_receipts,
        revenue_pit=rev_pit,
        revenue_sales_tax=rev_sales,
        revenue_bpol=rev_bpol,
        revenue_cit=rev_cit,
        revenue_grt=rev_grt,
        revenue_property=rev_property,
        revenue_utility=rev_utility,
        total_local_revenue=total_local,
        cumulative_revenue=cumulative_local,
    )

    # ── NPV calculations ───────────────────────────────────────────────────────
    disc_rate = rates.get_discount_rate(inputs.discount_type)

    npv_local = present_value(total_local, disc_rate)

    # Breakeven: project year and calendar year
    be_project_yr = breakeven_year(
        total_local,
        incentive_cost,
        discount_rate=disc_rate,
        start_year=1,
    )
    be_calendar_yr = (
        (inputs.project_start_year + be_project_yr - 1)
        if be_project_yr is not None
        else None
    )

    # Cumulative revenue by year dict
    cum_by_yr = {
        calendar_years[i]: round(cumulative_local[i], 2)
        for i in range(inputs.analysis_years)
    }

    # ── Assemble FiscalSummary ─────────────────────────────────────────────────
    summary = FiscalSummary(
        # Input echo
        state=inputs.state,
        city=inputs.city,
        direct_jobs=inputs.direct_jobs,
        average_salary=inputs.average_salary,
        capital_investment=inputs.capital_investment,
        project_start_year=inputs.project_start_year,
        analysis_years=inputs.analysis_years,

        # Employment
        total_direct_jobs_y1=direct_jobs[0] if direct_jobs else 0.0,
        total_jobs_at_maturity=total_jobs[-1] if total_jobs else 0.0,
        employment_multiplier=rates.rims2.get("employment_mult", 0.0),

        # Year 1 revenue breakdown
        y1_revenue_pit=rev_pit[0]      if rev_pit      else 0.0,
        y1_revenue_sales=rev_sales[0]  if rev_sales    else 0.0,
        y1_revenue_bpol=rev_bpol[0]    if rev_bpol     else 0.0,
        y1_revenue_cit=rev_cit[0]      if rev_cit      else 0.0,
        y1_revenue_grt=rev_grt[0]      if rev_grt      else 0.0,
        y1_revenue_property=rev_property[0] if rev_property else 0.0,
        y1_revenue_utility=rev_utility[0]   if rev_utility  else 0.0,
        y1_total_revenue=total_local[0] if total_local else 0.0,

        # NPV
        npv_total_revenue=npv_local,
        npv_incentive_cost=incentive_cost,
        discount_rate_used=disc_rate,

        # Breakeven
        cumulative_revenue_by_year=cum_by_yr,
        breakeven_year=be_project_yr,
        breakeven_calendar_year=be_calendar_yr,
        total_10yr_revenue=sum(total_local),

        # Rates used
        pit_effective_rate=rates.pit_effective_rate,
        sales_tax_rate=rates.sales_tax_rate,
        property_tax_rate=rates.property_tax_rate,
        cit_rate=rates.cit_rate,
        grt_rate=rates.grt_rate,
        bpol_rate=rates.bpol_rate_professional,
    )

    return ts, summary
