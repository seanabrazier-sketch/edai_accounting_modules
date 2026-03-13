"""
location_scoring/scoring_engine.py
KPMG min-max scalar scoring engine for the EDai Location Scoring module.

Seven-step pipeline
-------------------
1. Load raw values for all 181 cities from city_data.json.
2. For log-flagged variables, apply: transformed = ln(raw + 1).
3. Score each variable on a 1–5 scale:
     Higher-is-better: score = ((v - min) / (max - min)) * 4 + 1
     Lower-is-better:  score = ((max - v) / (max - min)) * 4 + 1
     No-variance edge case: score = 3.0 for all cities.
4. Apply user weight: weighted_score = score × weight.
5. Aggregate category scores per city.
6. Sum total score across all categories.
7. Rank all 181 cities descending by total score.

Post-scoring validation asserts each variable's scores ∈ [1.0, 5.0].
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from .models import CityRecord, ScoringConfig, ScoringResult, VariableSpec

logger = logging.getLogger(__name__)

# Score bounds defined by the KPMG min-max scalar
_SCORE_MIN = 1.0
_SCORE_MAX = 5.0
_SCORE_MID = 3.0  # assigned when max == min (no variance)
_SCORE_TOLERANCE = 1e-6  # floating-point guard for validation


# ── Internal helpers ────────────────────────────────────────────────────────

def _safe_log(value: float) -> float:
    """ln(value + 1), guarded against negatives."""
    return math.log(max(0.0, value) + 1.0)


def _compute_variable_values(
    cities: List[CityRecord],
    spec: VariableSpec,
    medians: Dict[str, float],
    missing_tracker: Dict[str, List[str]],
) -> Tuple[List[float], List[str]]:
    """
    Return (transformed_values, city_state_list) in the same order as `cities`.

    Missing raw values are replaced with the cross-city median for that variable.
    Log transform is applied after median substitution.
    """
    values: List[float] = []
    city_labels: List[str] = []

    for city in cities:
        raw = city.raw_values.get(spec.name)
        if raw is None or not math.isfinite(raw):
            # Substitute median and record the gap
            raw = medians.get(spec.name, 0.0)
            missing_tracker.setdefault(city.city_state, []).append(spec.name)
            logger.warning(
                "City '%s' missing variable '%s'; substituting median %.4f",
                city.city_state, spec.name, raw,
            )

        if spec.log_transform:
            raw = _safe_log(raw)

        values.append(raw)
        city_labels.append(city.city_state)

    return values, city_labels


def _minmax_score(value: float, vmin: float, vmax: float, higher_is_better: bool) -> float:
    """
    Apply the KPMG min-max scalar to a single value.
    Returns a score in [1.0, 5.0].
    Edge case: if vmax == vmin, return the midpoint 3.0.
    """
    spread = vmax - vmin
    if spread == 0:
        return _SCORE_MID

    if higher_is_better:
        score = ((value - vmin) / spread) * 4.0 + 1.0
    else:
        score = ((vmax - value) / spread) * 4.0 + 1.0

    # Clamp to guard against floating-point drift
    return max(_SCORE_MIN, min(_SCORE_MAX, score))


def _compute_medians(cities: List[CityRecord], specs: List[VariableSpec]) -> Dict[str, float]:
    """Pre-compute the cross-city median for each variable (for missing-value imputation)."""
    medians: Dict[str, float] = {}
    for spec in specs:
        vals = [
            c.raw_values[spec.name]
            for c in cities
            if spec.name in c.raw_values and math.isfinite(c.raw_values[spec.name])
        ]
        if not vals:
            medians[spec.name] = 0.0
        else:
            vals_sorted = sorted(vals)
            n = len(vals_sorted)
            mid = n // 2
            medians[spec.name] = (
                vals_sorted[mid] if n % 2 == 1
                else (vals_sorted[mid - 1] + vals_sorted[mid]) / 2.0
            )
    return medians


# ── Main scoring function ────────────────────────────────────────────────────

def score_cities(
    cities: List[CityRecord],
    specs: List[VariableSpec],
    config: ScoringConfig,
) -> List[ScoringResult]:
    """
    Run the full 7-step scoring pipeline and return a ranked list of ScoringResults.

    Parameters
    ----------
    cities : list of CityRecord
        All cities with raw_values populated.
    specs : list of VariableSpec
        Variable definitions.  Only specs whose name appears in `config.weights`
        with a positive weight are scored.
    config : ScoringConfig
        Must already be normalized (weights sum to 100).

    Returns
    -------
    list of ScoringResult, sorted by total_score descending (rank 1 = best).
    """
    # Filter to active specs (positive weight, name in config)
    active_specs = [
        s for s in specs
        if config.weights.get(s.name, 0.0) > 0
    ]
    logger.info("Scoring %d cities across %d variables", len(cities), len(active_specs))

    # ── Step 1 + 2: Pre-compute medians and collect (possibly log-transformed) values ──
    medians = _compute_medians(cities, active_specs)
    missing_tracker: Dict[str, List[str]] = {}   # city_state → list of missing varnames

    # variable_matrix[var_name] = list of transformed values, one per city (same order)
    variable_matrix: Dict[str, List[float]] = {}
    for spec in active_specs:
        vals, _ = _compute_variable_values(cities, spec, medians, missing_tracker)
        variable_matrix[spec.name] = vals

    # ── Step 3: Compute 1–5 scores for every city × variable ──────────────────
    # raw_scores[var_name][city_idx] = unweighted 1–5 score
    raw_scores: Dict[str, List[float]] = {}
    validation_failures: List[str] = []

    for spec in active_specs:
        vals = variable_matrix[spec.name]
        vmin = min(vals)
        vmax = max(vals)

        scores = [_minmax_score(v, vmin, vmax, spec.higher_is_better) for v in vals]

        # Post-scoring validation: all scores must be in [1.0, 5.0]
        out_of_bounds = [
            (i, s) for i, s in enumerate(scores)
            if s < _SCORE_MIN - _SCORE_TOLERANCE or s > _SCORE_MAX + _SCORE_TOLERANCE
        ]
        if out_of_bounds:
            for city_idx, bad_score in out_of_bounds:
                logger.error(
                    "Validation FAIL: variable '%s', city '%s', score=%.6f (expected 1–5)",
                    spec.name, cities[city_idx].city_state, bad_score,
                )
            validation_failures.append(spec.name)

        raw_scores[spec.name] = scores

    if validation_failures:
        logger.warning(
            "Score-range validation FAILED for %d variable(s): %s",
            len(validation_failures), validation_failures,
        )

    # Build a spec lookup for category info
    spec_by_name = {s.name: s for s in active_specs}

    # ── Steps 4–6: Apply weights, aggregate per category, sum total ─────────
    results: List[ScoringResult] = []

    for city_idx, city in enumerate(cities):
        variable_scores: Dict[str, float] = {}
        category_scores: Dict[str, float] = {}

        for var_name, scores in raw_scores.items():
            weight = config.weights.get(var_name, 0.0)
            weighted = scores[city_idx] * (weight / 100.0)   # weight is a percentage
            variable_scores[var_name] = weighted

            cat = spec_by_name[var_name].category
            category_scores[cat] = category_scores.get(cat, 0.0) + weighted

        total_score = sum(variable_scores.values())

        results.append(ScoringResult(
            city_name=city.city_name,
            state=city.state,
            city_state=city.city_state,
            metro=city.metro,
            total_score=total_score,
            category_scores=category_scores,
            variable_scores=variable_scores,
            missing_vars=missing_tracker.get(city.city_state, []),
        ))

    # ── Step 7: Rank descending by total_score ──────────────────────────────
    results.sort(key=lambda r: r.total_score, reverse=True)
    for rank, result in enumerate(results, start=1):
        result.rank = rank

    logger.info(
        "Scoring complete. Top city: %s (%.4f), Bottom: %s (%.4f)",
        results[0].city_state, results[0].total_score,
        results[-1].city_state, results[-1].total_score,
    )

    return results


# ── Convenience: score single variable (useful for debugging) ────────────────

def score_single_variable(
    cities: List[CityRecord],
    spec: VariableSpec,
) -> Dict[str, float]:
    """
    Return a dict of city_state → unweighted 1–5 score for one variable.
    Useful for debugging and spot-checking against Excel.
    """
    medians = _compute_medians(cities, [spec])
    missing_tracker: Dict[str, List[str]] = {}
    vals, labels = _compute_variable_values(cities, spec, medians, missing_tracker)

    vmin, vmax = min(vals), max(vals)
    return {
        label: _minmax_score(v, vmin, vmax, spec.higher_is_better)
        for label, v in zip(labels, vals)
    }
