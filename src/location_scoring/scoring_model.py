"""
location_scoring/scoring_model.py
Public API entry point for the EDai Location Scoring engine.

Usage (from Python)
-------------------
    from location_scoring.scoring_model import run_scoring, get_categories

    results = run_scoring()                 # equal weights, all 181 cities
    for r in results[:10]:
        print(r.rank, r.city_state, r.total_score)

    # Custom weights (subset of variables, any positive values)
    from location_scoring.models import ScoringConfig
    config = ScoringConfig(weights={
        "2021 Population_All": 3.0,
        "2021 Bach Share Adults": 2.0,
        "Foodie score": 1.0,
    })
    results = run_scoring(config=config)

Usage (__main__)
----------------
    python -m location_scoring.scoring_model
    python -m location_scoring.scoring_model --validate
"""
from __future__ import annotations

import logging
import sys
from typing import List, Optional

from .data_loader import (
    get_all_cities,
    get_categories,
    get_default_weights,
    get_variable_specs,
)
from .models import ScoringConfig, ScoringResult
from .scoring_engine import score_cities

logger = logging.getLogger(__name__)


# ── Public API ───────────────────────────────────────────────────────────────

def run_scoring(
    config: Optional[ScoringConfig] = None,
) -> List[ScoringResult]:
    """
    Score all 181 cities and return a ranked list of ScoringResult.

    Parameters
    ----------
    config : ScoringConfig | None
        Weight configuration.  If None, uses equal weights across all variables.
        Weights are automatically normalized to sum to 100 before scoring.

    Returns
    -------
    list of ScoringResult, sorted by total_score descending (rank 1 = best).
    """
    specs  = get_variable_specs()
    cities = get_all_cities()

    if config is None:
        config = get_default_weights()
        logger.info("No config provided — using equal weights.")
    else:
        # Always normalize before scoring so weights sum to 100
        config = config.normalize()
        logger.info("User config normalized: sum=%.2f", config.total())

    return score_cities(cities, specs, config)


def get_top_n(n: int = 20, config: Optional[ScoringConfig] = None) -> List[ScoringResult]:
    """Return the top-N cities by score."""
    return run_scoring(config)[:n]


def get_categories() -> List[str]:
    """Return all variable category names in dataset order."""
    from .data_loader import get_categories as _gc
    return _gc()


# ── __main__ block ───────────────────────────────────────────────────────────

def _print_results_table(results: List[ScoringResult], n: int = 20) -> None:
    print(f"\n{'Rank':>4}  {'City':<35} {'State':<20} {'Score':>8}  {'Missing':>7}")
    print("-" * 82)
    for r in results[:n]:
        missing_str = f"{len(r.missing_vars)}v" if r.missing_vars else "—"
        print(f"{r.rank:>4}  {r.city_name:<35} {r.state:<20} {r.total_score:>8.4f}  {missing_str:>7}")


def _print_category_breakdown(result: ScoringResult) -> None:
    print(f"\n  Category breakdown for #{result.rank} {result.city_state}:")
    for cat, score in sorted(result.category_scores.items(), key=lambda x: -x[1]):
        print(f"    {cat:<30}  {score:.4f}")


def _validate(results: List[ScoringResult]) -> bool:
    """
    Validation checks:
    1. Exactly 181 cities scored.
    2. All ranks unique and contiguous 1..N.
    3. Scores monotonically non-increasing (sorted correctly).
    4. Each city has ≥1 variable score > 0.
    """
    print("\n=== VALIDATION ===")
    ok = True

    # Check count
    if len(results) == 181:
        print(f"  ✅ City count: {len(results)}")
    else:
        print(f"  ❌ City count: {len(results)} (expected 181)")
        ok = False

    # Check ranks
    ranks = [r.rank for r in results]
    if ranks == list(range(1, len(results) + 1)):
        print(f"  ✅ Ranks: 1–{len(results)} contiguous")
    else:
        print(f"  ❌ Rank sequence broken: {ranks[:10]}…")
        ok = False

    # Check monotonic scores
    scores = [r.total_score for r in results]
    if all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)):
        print(f"  ✅ Scores: monotonically non-increasing")
    else:
        print(f"  ❌ Scores not properly sorted")
        ok = False

    # Check all scores > 0
    zero_scores = [r.city_state for r in results if r.total_score <= 0]
    if not zero_scores:
        print(f"  ✅ All cities have positive total scores")
    else:
        print(f"  ❌ Cities with zero/negative scores: {zero_scores}")
        ok = False

    # Score range sanity: total score = sum of (1-5 score * weight/100)
    # With equal weights across 147 vars, each var weight = 100/147 ≈ 0.6803
    # Weighted score per var ∈ [1 * 0.6803/100, 5 * 0.6803/100] = [0.0068, 0.034]...
    # Actually total = sum over all vars of (score_i * weight_i / 100)
    # With equal weights: total ≈ 147 * avg_score * (100/147) / 100 = avg_score
    # So total score should be between ~1 and ~5
    score_min = min(scores)
    score_max = max(scores)
    if 1.0 <= score_min and score_max <= 5.0:
        print(f"  ✅ Score range: [{score_min:.4f}, {score_max:.4f}] within [1, 5]")
    else:
        print(f"  ⚠️  Score range: [{score_min:.4f}, {score_max:.4f}] — check if within expected bounds")

    print(f"\n  Overall: {'PASS ✅' if ok else 'FAIL ❌'}")
    return ok


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,  # suppress info noise during CLI run
        format="%(levelname)s  %(name)s  %(message)s",
    )

    validate_mode = "--validate" in sys.argv

    print("=" * 82)
    print("EDai Location Scoring Engine — equal weights, 181 cities")
    print("=" * 82)

    results = run_scoring()

    # Print top 20
    _print_results_table(results, n=20)

    # Category breakdown for #1 and #2
    for r in results[:2]:
        _print_category_breakdown(r)

    # Bottom 5
    print(f"\n  ... (cities 3–{len(results)-5}) ...")
    print(f"\n{'Rank':>4}  {'City':<35} {'State':<20} {'Score':>8}")
    print("-" * 70)
    for r in results[-5:]:
        print(f"{r.rank:>4}  {r.city_name:<35} {r.state:<20} {r.total_score:>8.4f}")

    # Stats
    scores = [r.total_score for r in results]
    print(f"\n  Score stats: min={min(scores):.4f}  max={max(scores):.4f}  "
          f"mean={sum(scores)/len(scores):.4f}")

    if validate_mode:
        ok = _validate(results)
        sys.exit(0 if ok else 1)
