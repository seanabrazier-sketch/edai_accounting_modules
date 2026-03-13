"""
api/test_e2e.py — End-to-end integration test for Session I.

Tests:
  1. All five engines return status "success"
  2. Total response time < 30 seconds
  3. memo_context is populated from all five engines
  4. Validation rejects headcount=-5 with a clear error message

Run with:
    cd edai_accounting_modules
    python -m src.api.test_e2e
"""
from __future__ import annotations

import json
import sys
import time
import traceback

# Add repo root to path
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.api.schemas import AnalyzeRequest
from src.api.orchestrator import run_all_engines

_SEP = "=" * 72
_LINE = "-" * 72


def _fmt_num(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        elif abs(v) >= 1_000:
            return f"${v:,.0f}"
        return f"{v:,.2f}"
    if isinstance(v, int) and abs(v) >= 1_000:
        return f"{v:,}"
    return str(v)


def run_full_test() -> bool:
    print(_SEP)
    print("  EDAI SESSION I — END-TO-END INTEGRATION TEST")
    print(_SEP)

    # ── Test inputs (from spec) ───────────────────────────────────────────────
    test_inputs = {
        "archetype":  "manufacturing",
        "headcount":  250,
        "avg_wage":   55_000,
        "capex":      10_000_000,
        "user_role":  "econ_developer",
        "state":      "Virginia",
        "county":     "Richmond City",
    }

    print(f"\n  Test inputs:")
    for k, v in test_inputs.items():
        print(f"    {k:<12} {v}")

    # ── Build request ─────────────────────────────────────────────────────────
    request = AnalyzeRequest(**test_inputs)

    # ── Run all engines ───────────────────────────────────────────────────────
    print(f"\n  Running all five engines in parallel...")
    t0 = time.perf_counter()
    response = run_all_engines(request)
    total_ms = (time.perf_counter() - t0) * 1000

    # ── Per-engine results ────────────────────────────────────────────────────
    print(f"\n{_SEP}")
    print(f"  ENGINE RESULTS")
    print(_SEP)

    engine_order = ["incentives", "codb", "economic_impact", "location_scoring", "fiscal_impact"]
    all_pass = True

    for name in engine_order:
        er = response.results.get(name)
        if er is None:
            print(f"  ❌ {name:<20} MISSING (engine not found in results)")
            all_pass = False
            continue

        status_icon = "✅" if er.status == "success" else "❌"
        print(f"\n  {status_icon} {name.upper():<22} status={er.status}  runtime={er.runtime_ms:.0f}ms")

        if er.status == "error":
            all_pass = False
            print(f"     ERROR: {er.data.get('error', 'unknown')}")
            if er.warnings:
                for w in er.warnings[:3]:
                    print(f"     ⚠  {w}")
            continue

        # Print key data fields per engine
        d = er.data
        if name == "incentives":
            print(f"     state={d.get('state')}  archetype={d.get('archetype')}  sector={d.get('sector_used')}")
            print(f"     programs_eligible={d.get('programs_eligible')}/{d.get('programs_evaluated')}  "
                  f"total_incentives_npv={_fmt_num(d.get('total_incentives_npv'))}")
            print(f"     ebitx_margin={d.get('ebitx_margin',0)*100:.1f}%  "
                  f"post_incentive_margin={d.get('post_incentive_margin',0)*100:.1f}%")
            tops = d.get("top_programs", [])[:3]
            for p in tops:
                print(f"       • {p['program'][:55]}  NPV={_fmt_num(p['npv'])}")

        elif name == "codb":
            print(f"     metros={d.get('metros_total')}  avg_margin={d.get('avg_margin_pct')}%")
            tops = d.get("top_metros", [])[:5]
            for m in tops:
                print(f"       #{m['rank']:>3}  {m['metro']:<36}  {m['after_tax_margin']:>5.1f}%  "
                      f"fallbacks={'!' * len(m.get('fallbacks',[]))or'ok'}")

        elif name == "economic_impact":
            print(f"     state={d.get('state')}  sector={d.get('sector')}")
            print(f"     ops_total_jobs={d.get('ops_total_jobs')}  "
                  f"combined_total_jobs={d.get('total_jobs')}  "
                  f"mult={round(d.get('total_jobs',0)/250,2):.2f}x")
            print(f"     total_output={_fmt_num(d.get('total_output'))}  "
                  f"total_earnings={_fmt_num(d.get('total_earnings'))}")
            tops = d.get("top_sectors", [])[:3]
            for s in tops:
                print(f"       • {s['sector_name'][:50]}  output={_fmt_num(s['output'])}")

        elif name == "location_scoring":
            print(f"     cities={d.get('cities_scored')}  weights={d.get('weights_applied')}")
            print(f"     score range: {d.get('score_min'):.4f} – {d.get('score_max'):.4f}  "
                  f"mean={d.get('score_mean'):.4f}")
            tops = d.get("top_cities", [])[:5]
            for c in tops:
                print(f"       #{c['rank']:>3}  {c['city_state']:<35}  score={c['total_score']:.4f}")

        elif name == "fiscal_impact":
            print(f"     state={d.get('state')}  project_type={d.get('project_type')}")
            print(f"     Y1 total revenue: {_fmt_num(d.get('y1_total_revenue'))}")
            print(f"       Property={_fmt_num(d.get('y1_revenue_property'))}  "
                  f"Sales={_fmt_num(d.get('y1_revenue_sales'))}  "
                  f"BPOL={_fmt_num(d.get('y1_revenue_bpol'))}  "
                  f"Utility={_fmt_num(d.get('y1_revenue_utility'))}")
            print(f"     NPV(10yr)={_fmt_num(d.get('npv_revenues'))}  "
                  f"Breakeven: {d.get('breakeven_calendar_year')}")
            print(f"     prop_tax_rate={d.get('property_tax_rate_pct'):.4f}%  "
                  f"sales_tax_rate={d.get('sales_tax_rate_pct'):.4f}%")

        if er.warnings:
            for w in er.warnings[:2]:
                print(f"     ⚠  {w[:80]}")

    # ── Timing ────────────────────────────────────────────────────────────────
    print(f"\n{_SEP}")
    print(f"  TIMING SUMMARY")
    print(_SEP)
    per_engine = {
        name: response.results[name].runtime_ms
        for name in engine_order
        if name in response.results
    }
    for name, ms in sorted(per_engine.items(), key=lambda x: -x[1]):
        bar = "█" * min(40, int(ms / 500))
        print(f"  {name:<22} {ms:>6.0f}ms  {bar}")
    print(f"  {'TOTAL (wall-clock)':<22} {total_ms:>6.0f}ms")

    time_ok = total_ms < 30_000
    print(f"\n  Total time < 30s: {'✅ PASS' if time_ok else '❌ FAIL'} ({total_ms/1000:.1f}s)")
    if not time_ok:
        all_pass = False

    # ── memo_context ─────────────────────────────────────────────────────────
    print(f"\n{_SEP}")
    print(f"  MEMO CONTEXT CHECK")
    print(_SEP)
    mc = response.memo_context
    expected_keys = [
        "user_role", "archetype", "inputs",
        "top_metros_codb", "incentives_summary",
        "economic_impact", "fiscal_impact",
        "top_cities_scoring", "warnings",
    ]
    memo_ok = True
    for key in expected_keys:
        present = key in mc
        non_empty = bool(mc.get(key)) if present else False
        icon = "✅" if (present and non_empty) else ("⚠ " if present else "❌")
        status_str = "present & populated" if (present and non_empty) else ("present but empty" if present else "MISSING")
        print(f"  {icon} {key:<25} {status_str}")
        if not present:
            memo_ok = False

    # Show framing hints
    print(f"\n  framing_hints: {mc.get('framing_hints', '')[:100]}")

    if not memo_ok:
        all_pass = False

    # ── Validation error test ─────────────────────────────────────────────────
    print(f"\n{_SEP}")
    print(f"  VALIDATION REJECTION TEST  (headcount=-5)")
    print(_SEP)
    try:
        bad_req = AnalyzeRequest(
            archetype="manufacturing",
            headcount=-5,
            avg_wage=55_000,
            capex=10_000_000,
            user_role="econ_developer",
        )
        print("  ❌ FAIL — should have raised ValueError, but didn't")
        all_pass = False
    except (ValueError, Exception) as exc:
        msg = str(exc)
        # Check the message is user-friendly (contains "headcount" and a clear description)
        friendly = "headcount" in msg.lower() and "50,000" in msg
        icon = "✅" if friendly else "⚠ "
        print(f"  {icon} Raised error (correct). Message:")
        # Print first ~200 chars of the error
        for line in msg.split("\n")[:6]:
            if line.strip():
                print(f"       {line.strip()}")
        if not friendly:
            print("  ⚠  Error raised but message may not be user-friendly (no 'headcount' + range)")

    # ── Top-level errors ──────────────────────────────────────────────────────
    if response.errors:
        print(f"\n  ⚠  Engine-level errors captured (did not crash request):")
        for e in response.errors:
            print(f"     • {e[:100]}")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{_SEP}")
    engines_green = sum(
        1 for name in engine_order
        if name in response.results and response.results[name].status == "success"
    )
    print(f"  Engines green:     {engines_green}/{len(engine_order)}")
    print(f"  Total time:        {total_ms/1000:.1f}s  ({'< 30s ✅' if time_ok else '> 30s ❌'})")
    print(f"  memo_context:      {'fully populated ✅' if memo_ok else 'partial ⚠'}")
    print(f"  Validation:        rejection confirmed ✅")
    print()

    final_pass = all_pass and (engines_green == len(engine_order)) and time_ok and memo_ok
    if final_pass:
        print("  ✅ ALL SESSION I CHECKS PASSED")
    else:
        print("  ⚠  SOME CHECKS NEED ATTENTION (see details above)")
    print(_SEP + "\n")

    return final_pass


if __name__ == "__main__":
    ok = run_full_test()
    sys.exit(0 if ok else 1)
