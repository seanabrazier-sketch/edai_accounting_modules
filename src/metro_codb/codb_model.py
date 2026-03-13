"""
metro_codb/codb_model.py
Public API entry point for the Metro Cost of Doing Business model.

Usage
-----
    from metro_codb.codb_model import run_archetype, run_all_archetypes

    # Run all metros for a single archetype, ranked by after-tax margin
    results = run_archetype("office")

    # Filter to a single metro
    result = run_archetype("office", metro_filter="Seattle, Washington")

    # Run all three archetypes in one call
    all_results = run_all_archetypes()

Command-line
------------
    python -m metro_codb.codb_model

TODO: seattle_comparison.py — 500-FTE Seattle benchmark comparison layer.
      Build in a future session once metro P&L baseline is validated.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from .codb_engine import compute_all_metros, compute_pnl
from .models import PnLResult
from .rates_loader import get_all_archetypes, get_all_metros, get_archetype, get_metro_rates

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_archetype(
    archetype_name: str,
    metro_filter: Optional[str] = None,
    sort_by_margin: bool = True,
) -> list[PnLResult]:
    """Run the CODB model for a single archetype.

    Parameters
    ----------
    archetype_name : str
        One of "office", "manufacturing", "distribution".
    metro_filter : str, optional
        If provided, compute for only this metro (exact or case-insensitive match).
        If None, compute for all available metros.
    sort_by_margin : bool
        If True (default), return results sorted descending by after_tax_margin.

    Returns
    -------
    list[PnLResult]
        One result per metro. If sort_by_margin is True, index 0 = highest margin.
    """
    archetype = get_archetype(archetype_name)

    if metro_filter is not None:
        # Single-metro mode
        mr = get_metro_rates(metro_filter)
        result = compute_pnl(mr, archetype)
        return [result]

    # All-metros mode
    all_metro_names = get_all_metros()
    metro_rates_list = [get_metro_rates(n) for n in all_metro_names]
    return compute_all_metros(metro_rates_list, archetype, sort_by_margin=sort_by_margin)


def run_all_archetypes(
    sort_by_margin: bool = True,
) -> dict[str, list[PnLResult]]:
    """Run the CODB model for all three archetypes across all metros.

    Returns
    -------
    dict[str, list[PnLResult]]
        Keys: "office", "manufacturing", "distribution".
        Values: list of PnLResult sorted descending by after_tax_margin (if sort_by_margin).
    """
    return {
        arch.name: run_archetype(arch.name, sort_by_margin=sort_by_margin)
        for arch in get_all_archetypes()
    }


def summary_table(
    results: list[PnLResult],
    top_n: Optional[int] = None,
) -> list[dict]:
    """Convert a list of PnLResults to a serialisable summary list.

    Parameters
    ----------
    results : list[PnLResult]
        Pre-sorted results from run_archetype or run_all_archetypes.
    top_n : int, optional
        If provided, return only the top_n entries.

    Returns
    -------
    list[dict]
        Each dict: rank, metro, archetype, after_tax_margin (%), key cost lines,
        and any fallback flags.
    """
    rows = results[:top_n] if top_n else results
    out = []
    for rank, r in enumerate(rows, start=1):
        row = {
            "rank":              rank,
            "metro":             r.metro,
            "archetype":         r.archetype,
            "after_tax_margin":  round(r.after_tax_margin * 100, 2),   # %
            "sales":             round(r.sales),
            "salaries":          round(r.salaries),
            "benefits_total":    round(r.benefits_total),
            "real_estate":       round(r.real_estate),
            "utilities":         round(r.utilities),
            "cogs":              round(r.cogs),
            "pretax_income":     round(r.pretax_income),
            "federal_tax":       round(r.federal_tax),
            "state_local_tax":   round(r.state_local_tax),
            "after_tax_income":  round(r.after_tax_income),
            "fallbacks":         r.fallbacks_used,
        }
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# CLI entry point  —  python -m metro_codb.codb_model
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(levelname)-8s %(name)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )


def _print_summary(
    arch_name: str,
    results: list[PnLResult],
    top_n: int = 10,
) -> None:
    rows = summary_table(results)
    n_metros = len(results)
    avg_margin = (
        sum(r.after_tax_margin for r in results) / n_metros if n_metros else 0.0
    )

    print(f"\n{'=' * 72}")
    print(f"  ARCHETYPE: {arch_name.upper()}   |   {n_metros} metros   |"
          f"   Avg margin: {avg_margin * 100:.1f}%")
    print(f"{'=' * 72}")
    hdr = f"{'Rank':>4}  {'Metro':<36}  {'Margin':>8}  {'Salaries':>10}  "
    hdr += f"{'RE':>10}  {'Fallbacks':>10}"
    print(hdr)
    print("-" * 80)

    for row in rows[:top_n]:
        fb_count = len(row["fallbacks"])
        print(
            f"{row['rank']:>4}  "
            f"{row['metro']:<36}  "
            f"{row['after_tax_margin']:>7.1f}%  "
            f"${row['salaries']:>9,.0f}  "
            f"${row['real_estate']:>9,.0f}  "
            f"{'!' * fb_count if fb_count else 'ok':>10}"
        )

    # Bottom 5
    if n_metros > top_n + 5:
        print(f"  … ({n_metros - top_n - 5} metros omitted) …")
        for row in rows[-(5):]:
            fb_count = len(row["fallbacks"])
            print(
                f"{row['rank']:>4}  "
                f"{row['metro']:<36}  "
                f"{row['after_tax_margin']:>7.1f}%  "
                f"${row['salaries']:>9,.0f}  "
                f"${row['real_estate']:>9,.0f}  "
                f"{'!' * fb_count if fb_count else 'ok':>10}"
            )


def main(argv: Optional[list[str]] = None) -> None:
    """Run all three archetypes and print ranking tables + validation summary."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Metro CODB — Cost of Doing Business engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--archetype", "-a", default=None,
                        choices=["office", "manufacturing", "distribution"],
                        help="Run one archetype only (default: all three)")
    parser.add_argument("--metro", "-m", default=None,
                        help="Filter to a single metro (partial name ok)")
    parser.add_argument("--top", "-n", type=int, default=10,
                        help="Number of top metros to show per archetype (default: 10)")
    parser.add_argument("--validate", "-v", action="store_true",
                        help="Print whitepaper benchmark validation table")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable DEBUG-level logging")
    args = parser.parse_args(argv)

    _setup_logging(verbose=args.verbose)

    # Whitepaper targets (after-tax margin, from Metro CODB spec)
    _TARGETS: dict[str, float] = {
        "office":         0.319,
        "manufacturing":  0.209,
        "distribution":   0.374,
    }
    _TOLERANCE = 0.005   # ±0.5 pp

    archetype_names = (
        [args.archetype] if args.archetype
        else ["office", "manufacturing", "distribution"]
    )

    all_results: dict[str, list[PnLResult]] = {}
    for arch_name in archetype_names:
        results = run_archetype(arch_name, metro_filter=args.metro)
        all_results[arch_name] = results
        _print_summary(arch_name, results, top_n=args.top)

    # ------------------------------------------------------------------
    # Validation table (against whitepaper benchmarks)
    # ------------------------------------------------------------------
    if args.validate or True:   # always print validation block
        print(f"\n{'=' * 72}")
        print("  WHITEPAPER BENCHMARK VALIDATION")
        print(f"{'=' * 72}")
        print(f"  {'Archetype':<16} {'Target':>8} {'Actual':>8} {'Delta':>8} {'Pass?':>6}")
        print(f"  {'-' * 50}")

        all_pass = True
        for arch_name, results in all_results.items():
            if not results:
                continue
            avg_margin = sum(r.after_tax_margin for r in results) / len(results)
            target = _TARGETS.get(arch_name)
            if target is None:
                continue
            delta = avg_margin - target
            passed = abs(delta) <= _TOLERANCE
            if not passed:
                all_pass = False
            flag = "  PASS" if passed else "  FAIL ←"
            print(
                f"  {arch_name:<16} "
                f"{target * 100:>7.1f}% "
                f"{avg_margin * 100:>7.1f}% "
                f"{delta * 100:>+7.2f}pp"
                f"{flag}"
            )

        print(f"\n  Overall: {'PASS ✓' if all_pass else 'FAIL — see delta column'}")

        # El Paso rank check
        for arch_name in ("office", "manufacturing"):
            results = all_results.get(arch_name, [])
            if not results:
                continue
            ep_ranks = [
                i + 1 for i, r in enumerate(results)
                if "el paso" in r.metro.lower()
            ]
            if ep_ranks:
                rank = ep_ranks[0]
                passed = rank <= 10
                flag = "PASS" if passed else f"FAIL (rank={rank})"
                print(f"  El Paso {arch_name:<14} rank {rank:>3}/~{len(results):<3}  {flag}")
            else:
                print(f"  El Paso {arch_name:<14} NOT FOUND in results")

    print()


if __name__ == "__main__":
    main()
