"""
api/orchestrator.py — Parallel engine runner.

Accepts an AnalyzeRequest, dispatches all five engines concurrently using
ThreadPoolExecutor, and assembles an AnalyzeResponse.

Engine isolation: if any single engine raises an exception, the error is
caught, logged, and returned as an EngineResult(status="error") — the
overall request always completes.
"""
from __future__ import annotations

import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from .input_mappers import (
    build_economic_inputs,
    build_fiscal_inputs,
    build_incentives_input,
    get_default_weights_for_archetype,
)
from .memo_builder import build_memo_context
from .schemas import AnalyzeRequest, AnalyzeResponse, EngineResult

logger = logging.getLogger(__name__)

# Maximum threads for parallel engine execution
_MAX_WORKERS = 5


# ─────────────────────────────────────────────────────────────────────────────
# Individual engine runners — each returns (engine_name, EngineResult)
# ─────────────────────────────────────────────────────────────────────────────

def _run_incentives(request: AnalyzeRequest) -> Tuple[str, EngineResult]:
    engine = "incentives"
    t0 = time.perf_counter()
    warnings: List[str] = []

    if request.state_is_placeholder:
        warnings.append("No state provided — using Virginia as placeholder. Results are not state-specific.")

    try:
        # The accounting engine uses legacy absolute imports (e.g. `from accounting.data_store`)
        # that require `src/` on sys.path.  Add it if not already present.
        import sys, pathlib
        _src = str(pathlib.Path(__file__).parent.parent)
        if _src not in sys.path:
            sys.path.insert(0, _src)

        from ..accounting.accounting_model import run_incentives_model
        inp = build_incentives_input(request)
        result = run_incentives_model(inp)

        # Collect any warnings from the engine itself
        warnings.extend(result.warnings or [])

        data: Dict[str, Any] = {
            "state":                 result.state,
            "archetype":             result.archetype,
            "sector_used":           result.sector_used,
            "programs_evaluated":    result.programs_evaluated,
            "programs_eligible":     result.programs_eligible,
            "programs_errored":      result.programs_errored,
            "total_incentives_npv":  result.total_incentives_npv,
            "npv_net_profit":        result.npv_net_profit,
            "npv_sales":             result.npv_sales,
            "ebitx_margin":          result.ebitx_margin,
            "post_incentive_npv":    result.post_incentive_npv,
            "post_incentive_margin": result.post_incentive_margin,
            # Top 5 eligible programs by NPV
            "top_programs": [
                {
                    "program":         p.program,
                    "incentive_type":  p.incentive_type,
                    "npv":             p.npv,
                }
                for p in sorted(
                    [p for p in result.programs if p.eligible],
                    key=lambda p: p.npv,
                    reverse=True,
                )[:5]
            ],
        }
        runtime_ms = (time.perf_counter() - t0) * 1000
        return engine, EngineResult(
            engine=engine, status="success",
            data=data, warnings=warnings, runtime_ms=runtime_ms,
        )

    except Exception as exc:
        runtime_ms = (time.perf_counter() - t0) * 1000
        logger.exception("Incentives engine failed")
        return engine, EngineResult(
            engine=engine, status="error",
            data={"error": str(exc)},
            warnings=warnings,
            runtime_ms=runtime_ms,
        )


def _run_codb(request: AnalyzeRequest) -> Tuple[str, EngineResult]:
    engine = "codb"
    t0 = time.perf_counter()
    warnings: List[str] = []

    try:
        from ..metro_codb.codb_model import run_archetype, summary_table

        results = run_archetype(request.archetype)   # all metros, sorted by margin

        # Collect fallback warnings from individual results
        for r in results:
            for fb in (r.fallbacks_used or []):
                msg = f"{r.metro}: {fb}"
                if msg not in warnings:
                    warnings.append(msg)

        rows = summary_table(results)

        data: Dict[str, Any] = {
            "archetype":    request.archetype,
            "metros_total": len(rows),
            "top_metros":   rows[:10],   # top 10 by after-tax margin
            "bottom_metros": rows[-5:],  # bottom 5 for contrast
            "avg_margin_pct": round(
                sum(r["after_tax_margin"] for r in rows) / len(rows), 2
            ) if rows else None,
        }
        runtime_ms = (time.perf_counter() - t0) * 1000
        return engine, EngineResult(
            engine=engine, status="success",
            data=data, warnings=warnings[:20], runtime_ms=runtime_ms,
        )

    except Exception as exc:
        runtime_ms = (time.perf_counter() - t0) * 1000
        logger.exception("CODB engine failed")
        return engine, EngineResult(
            engine=engine, status="error",
            data={"error": str(exc)},
            warnings=warnings,
            runtime_ms=runtime_ms,
        )


def _run_economic_impact(request: AnalyzeRequest) -> Tuple[str, EngineResult]:
    engine = "economic_impact"
    t0 = time.perf_counter()
    warnings: List[str] = []

    if request.state_is_placeholder:
        warnings.append("No state provided — using Virginia RIMS II multipliers as placeholder.")

    try:
        from ..economic_impact.impact_model import run_impact
        inp = build_economic_inputs(request)
        result = run_impact(inp)

        warnings.extend(result.warnings or [])

        ops   = result.operations
        constr = result.construction
        top5_sectors = sorted(
            result.sector_breakdown, key=lambda r: r.output, reverse=True
        )[:5]

        data: Dict[str, Any] = {
            "state":                     inp.state,
            "sector":                    inp.sector,
            "placeholder_used":          result.placeholder_multipliers_used,
            # Operations phase
            "ops_total_jobs":            round(ops.total_jobs, 1),
            "ops_total_earnings":        round(ops.total_earnings),
            "ops_total_output":          round(ops.total_output),
            "ops_total_value_added":     round(ops.total_value_added),
            "ops_bea_industry":          ops.bea_industry_name,
            "ops_de_employment_mult":    round(ops.de_employment_mult, 4),
            "ops_fd_output_mult":        round(ops.fd_output_mult, 4),
            # Construction phase
            "constr_total_jobs":         round(constr.total_jobs, 1),
            "constr_total_output":       round(constr.total_output),
            "constr_total_captured":     round(constr.total_captured),
            # Combined totals
            "total_jobs":                round(result.total_jobs, 1),
            "total_earnings":            round(result.total_earnings),
            "total_output":              round(result.total_output),
            "total_value_added":         round(result.total_value_added),
            # Sector breakdown
            "top_sectors": [
                {
                    "sector_name": s.sector_name,
                    "output":      round(s.output),
                    "employment":  round(s.employment, 1),
                    "earnings":    round(s.earnings),
                }
                for s in top5_sectors
            ],
        }
        runtime_ms = (time.perf_counter() - t0) * 1000
        return engine, EngineResult(
            engine=engine, status="success",
            data=data, warnings=warnings, runtime_ms=runtime_ms,
        )

    except Exception as exc:
        runtime_ms = (time.perf_counter() - t0) * 1000
        logger.exception("Economic Impact engine failed")
        return engine, EngineResult(
            engine=engine, status="error",
            data={"error": str(exc)},
            warnings=warnings,
            runtime_ms=runtime_ms,
        )


def _run_location_scoring(request: AnalyzeRequest) -> Tuple[str, EngineResult]:
    engine = "location_scoring"
    t0 = time.perf_counter()
    warnings: List[str] = []

    try:
        from ..location_scoring.scoring_model import run_scoring

        config = get_default_weights_for_archetype(request.archetype)
        results = run_scoring(config=config)

        # Build serializable top-10 and bottom-5 city rows
        def _city_row(r) -> dict:
            return {
                "rank":           r.rank,
                "city_state":     r.city_state,
                "city_name":      r.city_name,
                "state":          r.state,
                "total_score":    round(r.total_score, 4),
                "category_scores": {
                    cat: round(score, 4)
                    for cat, score in r.category_scores.items()
                },
                "missing_vars":   len(r.missing_vars),
            }

        scores = [r.total_score for r in results]

        data: Dict[str, Any] = {
            "archetype":       request.archetype,
            "cities_scored":   len(results),
            "top_cities":      [_city_row(r) for r in results],
            "bottom_cities":   [_city_row(r) for r in results[-5:]],
            "score_min":       round(min(scores), 4) if scores else None,
            "score_max":       round(max(scores), 4) if scores else None,
            "score_mean":      round(sum(scores) / len(scores), 4) if scores else None,
            "weights_applied": f"{request.archetype}-optimized" if config else "equal",
        }
        runtime_ms = (time.perf_counter() - t0) * 1000
        return engine, EngineResult(
            engine=engine, status="success",
            data=data, warnings=warnings, runtime_ms=runtime_ms,
        )

    except Exception as exc:
        runtime_ms = (time.perf_counter() - t0) * 1000
        logger.exception("Location Scoring engine failed")
        return engine, EngineResult(
            engine=engine, status="error",
            data={"error": str(exc)},
            warnings=warnings,
            runtime_ms=runtime_ms,
        )


def _run_fiscal_impact(request: AnalyzeRequest) -> Tuple[str, EngineResult]:
    engine = "fiscal_impact"
    t0 = time.perf_counter()
    warnings: List[str] = []

    if request.state_is_placeholder:
        warnings.append("No state provided — using Virginia for fiscal rates. Results are not state-specific.")
    if request.county_is_placeholder:
        warnings.append("No county provided — using Richmond City as placeholder for BPOL / utility tax.")

    try:
        from ..fiscal_impact.fiscal_model import analyze
        inp_dict = build_fiscal_inputs(request)
        result = analyze(inp_dict, incentive_cost=0.0)

        summary = result["summary"]
        ts = result["time_series"]
        rates = result["rates_used"]

        # Year 1 detailed breakdown (first row of time series)
        y1 = ts[0] if ts else {}

        data: Dict[str, Any] = {
            "state":                     inp_dict["state"],
            "city":                      inp_dict["city"],
            "project_type":              inp_dict["project_type"],
            # Summary
            "y1_total_revenue":          summary.get("y1_total_revenue"),
            "y1_revenue_property":       summary.get("y1_revenue_property"),
            "y1_revenue_sales":          summary.get("y1_revenue_sales"),
            "y1_revenue_bpol":           summary.get("y1_revenue_bpol"),
            "y1_revenue_pit":            summary.get("y1_revenue_pit"),
            "y1_revenue_cit":            summary.get("y1_revenue_cit"),
            "y1_revenue_utility":        summary.get("y1_revenue_utility"),
            "npv_revenues":              summary.get("npv_revenues"),
            "total_10yr_revenue":        summary.get("total_10yr_revenue"),
            "breakeven_project_year":    summary.get("breakeven_project_year"),
            "breakeven_calendar_year":   summary.get("breakeven_calendar_year"),
            # Rates
            "property_tax_rate_pct":     round(rates.get("property_tax_rate", 0) * 100, 4),
            "sales_tax_rate_pct":        round(rates.get("sales_tax_rate", 0) * 100, 4),
            "cit_rate_pct":              round(rates.get("cit_rate", 0) * 100, 4),
            "pit_effective_rate_pct":    round(rates.get("pit_effective_rate", 0) * 100, 4),
            # First 5 years of the time series
            "time_series_5yr":           ts[:5],
        }
        runtime_ms = (time.perf_counter() - t0) * 1000
        return engine, EngineResult(
            engine=engine, status="success",
            data=data, warnings=warnings, runtime_ms=runtime_ms,
        )

    except Exception as exc:
        runtime_ms = (time.perf_counter() - t0) * 1000
        logger.exception("Fiscal Impact engine failed")
        return engine, EngineResult(
            engine=engine, status="error",
            data={"error": str(exc)},
            warnings=warnings,
            runtime_ms=runtime_ms,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

# Engine dispatch table: (name, runner_fn)
_ENGINES = [
    ("incentives",        _run_incentives),
    ("codb",              _run_codb),
    ("economic_impact",   _run_economic_impact),
    ("location_scoring",  _run_location_scoring),
    ("fiscal_impact",     _run_fiscal_impact),
]


def run_all_engines(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run all five engines in parallel and assemble a single AnalyzeResponse.

    One engine failure never crashes the whole request — it produces an
    EngineResult with status="error" and the exception message in data.errors.
    """
    t_total = time.perf_counter()
    results: Dict[str, EngineResult] = {}
    top_errors: list[str] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {
            executor.submit(fn, request): name
            for name, fn in _ENGINES
        }
        for future in as_completed(futures):
            try:
                engine_name, engine_result = future.result()
                results[engine_name] = engine_result
                if engine_result.status == "error":
                    top_errors.append(
                        f"{engine_name}: {engine_result.data.get('error', 'unknown error')}"
                    )
            except Exception as exc:
                engine_name = futures[future]
                logger.exception("Unhandled exception in engine %s", engine_name)
                results[engine_name] = EngineResult(
                    engine=engine_name,
                    status="error",
                    data={"error": str(exc), "traceback": traceback.format_exc()},
                    warnings=[],
                    runtime_ms=0.0,
                )
                top_errors.append(f"{engine_name}: {str(exc)}")

    # Build response
    response = AnalyzeResponse(
        inputs=request,
        results=results,
        errors=top_errors,
    )

    # Attach memo context
    try:
        response.memo_context = build_memo_context(response)
    except Exception as exc:
        logger.exception("memo_builder failed")
        response.memo_context = {"error": str(exc)}

    total_ms = (time.perf_counter() - t_total) * 1000
    logger.info(
        "run_all_engines complete in %.0fms | engines=%s | errors=%d",
        total_ms,
        list(results.keys()),
        len(top_errors),
    )

    return response
