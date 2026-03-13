"""
employment.py — Employment trajectory and RIMS II multiplier calculations.

Computes year-by-year direct, indirect, and induced employment and payroll
for the analysis period.

RIMS II interpretation used here:
    The Type II Final-demand Employment multiplier (jobs per $1M of final demand)
    is converted to an "additional jobs per direct job" ratio by:
        additional_ratio = (employment_mult / direct_effect_mult) - 1
    where employment_mult and direct_effect_mult come from the RIMS2 dict.

    This gives additional indirect+induced jobs per 1 direct job.
"""

from __future__ import annotations
from typing import List, Tuple

from .models import ProjectInputs, LocationRates


def calculate_employment_trajectory(
    inputs: ProjectInputs,
    rates: LocationRates,
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    Compute direct, indirect, induced, and total employment for each year.

    Returns
    -------
    (direct_jobs, indirect_jobs, induced_jobs, total_jobs)
        Each is a list of length inputs.analysis_years.
    """
    ramp = inputs.get_employment_ramp()

    # ── RIMS II multiplier: additional jobs per direct job ────────────────────
    rims = rates.rims2
    total_mult   = rims.get("employment_mult", 1.0)
    direct_mult  = rims.get("direct_employment_mult", 1.0)

    # Guard against division by zero / degenerate values
    if direct_mult > 0 and total_mult > direct_mult:
        additional_per_direct = (total_mult / direct_mult) - 1.0
    else:
        additional_per_direct = max(0.0, total_mult - 1.0)

    # Split additional into ~60% indirect, ~40% induced (standard BEA convention)
    indirect_share  = 0.60
    induced_share   = 0.40

    direct_jobs:   List[float] = []
    indirect_jobs: List[float] = []
    induced_jobs:  List[float] = []
    total_jobs:    List[float] = []

    for frac in ramp:
        dj = inputs.direct_jobs * frac
        addl = dj * additional_per_direct
        ij = addl * indirect_share
        nj = addl * induced_share

        direct_jobs.append(dj)
        indirect_jobs.append(ij)
        induced_jobs.append(nj)
        total_jobs.append(dj + addl)

    return direct_jobs, indirect_jobs, induced_jobs, total_jobs


def calculate_payroll_trajectory(
    inputs: ProjectInputs,
    rates: LocationRates,
    direct_jobs: List[float],
    indirect_jobs: List[float],
    induced_jobs: List[float],
) -> Tuple[List[float], List[float], List[float]]:
    """
    Compute annual payroll for direct, indirect, and induced workers.

    Wages escalate at the ECI (Employment Cost Index) inflation rate.

    Returns
    -------
    (direct_payroll, indirect_payroll, induced_payroll)
    """
    eci = rates.eci_inflation
    state_avg_wage = rates.state_avg_annual_wage

    direct_payroll:   List[float] = []
    indirect_payroll: List[float] = []
    induced_payroll:  List[float] = []

    for yr_idx in range(inputs.analysis_years):
        # Salary grows with ECI each year
        inflation_factor = (1 + eci) ** yr_idx

        dp = direct_jobs[yr_idx] * inputs.average_salary * inflation_factor
        ip = indirect_jobs[yr_idx] * state_avg_wage * inflation_factor
        np_ = induced_jobs[yr_idx] * state_avg_wage * inflation_factor

        direct_payroll.append(dp)
        indirect_payroll.append(ip)
        induced_payroll.append(np_)

    return direct_payroll, indirect_payroll, induced_payroll


def estimate_gross_receipts(
    payroll: List[float],
    payroll_to_receipts_ratio: float,
) -> List[float]:
    """
    Estimate annual gross receipts from payroll using the IRS payroll-to-receipts ratio.
        gross_receipts = payroll / payroll_to_receipts_ratio
    """
    if payroll_to_receipts_ratio <= 0:
        payroll_to_receipts_ratio = 0.1052  # national average fallback
    return [p / payroll_to_receipts_ratio for p in payroll]
