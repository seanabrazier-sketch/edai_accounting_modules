"""
npv_engine.py — Net present value, cumulative revenue, and breakeven calculations.

All functions operate on plain Python lists (one value per year).
"""

from __future__ import annotations
from typing import List, Optional


def present_value(
    cash_flows: List[float],
    discount_rate: float,
    start_year: int = 1,
) -> float:
    """
    Compute the net present value of a cash flow stream.

    PV = sum( CF_t / (1 + r)^t )  for t = start_year, start_year+1, ...

    cash_flows[0] corresponds to project Year start_year.
    """
    pv = 0.0
    for i, cf in enumerate(cash_flows):
        t = start_year + i
        pv += cf / (1.0 + discount_rate) ** t
    return pv


def cumulative_sum(values: List[float]) -> List[float]:
    """Running cumulative sum."""
    result: List[float] = []
    total = 0.0
    for v in values:
        total += v
        result.append(total)
    return result


def breakeven_year(
    annual_revenues: List[float],
    incentive_cost: float,
    discount_rate: float = 0.0,
    start_year: int = 1,
) -> Optional[int]:
    """
    Return the project year in which cumulative (discounted) revenues
    first exceed incentive_cost.  Returns None if never exceeded.

    If discount_rate = 0, uses nominal (undiscounted) cumulative revenues.
    If incentive_cost = 0, always returns start_year (instantly positive).
    """
    if incentive_cost <= 0:
        return start_year

    cumulative = 0.0
    for i, rev in enumerate(annual_revenues):
        yr = start_year + i
        if discount_rate > 0:
            discounted = rev / (1.0 + discount_rate) ** yr
        else:
            discounted = rev
        cumulative += discounted
        if cumulative >= incentive_cost:
            return yr

    return None  # never breaks even within the window


def npv_by_stream(
    streams: dict,
    discount_rate: float,
    stream_keys: Optional[List[str]] = None,
) -> dict:
    """
    Compute NPV for each revenue stream dict.

    streams: {stream_name: [annual_values]}
    Returns: {stream_name: npv_value}
    """
    keys = stream_keys or list(streams.keys())
    return {k: present_value(streams[k], discount_rate) for k in keys if k in streams}


def irr(cash_flows: List[float], guess: float = 0.10, max_iter: int = 1000) -> Optional[float]:
    """
    Internal rate of return (Newton-Raphson).
    cash_flows[0] is typically negative (initial cost).
    Returns None if no convergence.
    """
    r = guess
    for _ in range(max_iter):
        # f(r) = sum(CF_t / (1+r)^t)
        f  = sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))
        # f'(r) = sum(-t * CF_t / (1+r)^(t+1))
        df = sum(-t * cf / (1 + r) ** (t + 1) for t, cf in enumerate(cash_flows) if t > 0)
        if df == 0:
            return None
        r_new = r - f / df
        if abs(r_new - r) < 1e-9:
            return r_new
        r = r_new
    return None
