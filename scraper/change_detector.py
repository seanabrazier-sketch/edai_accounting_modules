#!/usr/bin/env python3
"""
change_detector.py — Incentive Program Change Detection Engine
==============================================================
Loads data/bls_current.json (fresh BLS scrape) and the model's program
inventory, fuzzy-matches programs by name + state, and applies three
scenario flags:

  Scenario 1  unverified      — In model, NOT on BLS
  Scenario 2  new_candidate   — On BLS, NOT in model
  Scenario 3  parameters_changed — In both; detected parameter diffs
  (active)    no change

Usage
-----
  python scraper/change_detector.py
  python scraper/change_detector.py --bls data/bls_current.json --threshold 90
  python scraper/change_detector.py --output data/flagged.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE   = Path(__file__).parent
_ROOT   = _HERE.parent
_DATA   = _ROOT / "data"
_PROGRAMS_TXT = _ROOT / "src" / "accounting" / "incentive_programs.txt"

DEFAULT_BLS_PATH     = _DATA / "bls_current.json"
DEFAULT_OUTPUT_PATH  = _DATA / "flagged.json"
DEFAULT_THRESHOLD    = 90          # fuzzy match minimum confidence (0–100)

# Fields we compare for Scenario 3 diffs
COMPARABLE_FIELDS = [
    "jobs_threshold",
    "wage_threshold",
    "capex_threshold",
    "credit_rate",
    "award_cap",
    "carryforward_years",
    "refundable",
]

log = logging.getLogger("change_detector")


# ---------------------------------------------------------------------------
# Model inventory loader
# ---------------------------------------------------------------------------

def load_model_inventory() -> dict[str, dict[str, dict]]:
    """
    Build the model's program inventory from incentive_programs.txt.

    Returns:
      {
        "Alabama": {
          "Jobs Act Incentives: Jobs": { "in_model": True, ... },
          ...
        },
        ...
      }

    Parameters from the Python module files are not yet extracted here
    (they're embedded in module logic, not a clean data schema). The
    inventory captures program existence; parameter comparison relies on
    the BLS-scraped values vs the previous BLS baseline.
    """
    inventory: dict[str, dict[str, dict]] = {}

    if not _PROGRAMS_TXT.exists():
        log.error(f"incentive_programs.txt not found at {_PROGRAMS_TXT}")
        return inventory

    for line in _PROGRAMS_TXT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "_" not in line:
            continue
        state, prog_name = line.split("_", 1)
        if state not in inventory:
            inventory[state] = {}
        inventory[state][prog_name] = {
            "in_model": True,
            # Parameters are defined in Python module files, not easily
            # extracted to JSON without a dedicated extractor pass.
            # See: src/accounting/incentives/{state_slug}/{program_slug}.py
            "jobs_threshold":    None,
            "wage_threshold":    None,
            "capex_threshold":   None,
            "credit_rate":       None,
            "award_cap":         None,
            "carryforward_years": None,
            "refundable":        None,
        }

    total = sum(len(v) for v in inventory.values())
    log.info(f"Model inventory: {total} programs across {len(inventory)} states")
    return inventory


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def _fuzzy_score(a: str, b: str) -> float:
    """0–100 similarity score between two strings (case-insensitive)."""
    return SequenceMatcher(
        None,
        a.lower().strip(),
        b.lower().strip(),
    ).ratio() * 100


def fuzzy_match(
    candidate: str,
    choices: list[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> Optional[tuple[str, float]]:
    """
    Return (best_match, score) if score >= threshold, else None.
    Uses a two-pass approach: exact prefix match first, then ratio.
    """
    if not choices:
        return None

    best_name  = ""
    best_score = 0.0

    # Exact match wins immediately
    for c in choices:
        if candidate.lower().strip() == c.lower().strip():
            return (c, 100.0)

    # Fuzzy
    for c in choices:
        score = _fuzzy_score(candidate, c)
        if score > best_score:
            best_score = score
            best_name  = c

    if best_score >= threshold:
        return (best_name, best_score)
    return None


# ---------------------------------------------------------------------------
# Parameter diff
# ---------------------------------------------------------------------------

def compute_diff(
    model_params: dict[str, Any],
    bls_params: dict[str, Any],
) -> list[dict]:
    """
    Compare model parameters vs BLS-scraped parameters.
    Only flags a diff when BOTH sides have a non-null value and they differ.
    (If the model side is null, we can't confirm a change — we note it separately.)

    Returns list of diff records: [{"field", "model_value", "bls_value"}, ...]
    """
    diffs: list[dict] = []

    for field in COMPARABLE_FIELDS:
        m_val = model_params.get(field)
        b_val = bls_params.get(field)

        if m_val is None and b_val is None:
            continue   # Both unknown — no actionable diff

        if m_val is None and b_val is not None:
            # BLS has a value our model doesn't document — informational note
            diffs.append({
                "field":       field,
                "model_value": "not documented",
                "bls_value":   b_val,
                "diff_type":   "model_undocumented",
            })
            continue

        if m_val is not None and b_val is None:
            continue   # BLS didn't extract this field — not actionable

        # Both have values — compare
        # For floats, allow a small tolerance to avoid floating-point noise
        if isinstance(m_val, float) and isinstance(b_val, float):
            if abs(m_val - b_val) > 0.001:
                diffs.append({
                    "field":       field,
                    "model_value": m_val,
                    "bls_value":   b_val,
                    "diff_type":   "value_changed",
                })
        elif m_val != b_val:
            diffs.append({
                "field":       field,
                "model_value": m_val,
                "bls_value":   b_val,
                "diff_type":   "value_changed",
            })

    return diffs


# ---------------------------------------------------------------------------
# Main detection engine
# ---------------------------------------------------------------------------

def run_detection(
    bls_programs: list[dict],
    model_inventory: dict[str, dict[str, dict]],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """
    Apply three-scenario logic and return a structured flagged output dict.

    Output shape:
    {
      "run_at": "...",
      "summary": { ... },
      "unverified": [...],
      "new_candidates": [...],
      "parameters_changed": [...],
      "active": [...],
      "low_confidence_matches": [...],
    }
    """
    run_at = datetime.now(timezone.utc).isoformat()

    unverified:          list[dict] = []
    new_candidates:      list[dict] = []
    parameters_changed:  list[dict] = []
    active:              list[dict] = []
    low_confidence:      list[dict] = []

    # Track which model programs have been matched
    matched_model_programs: dict[str, set[str]] = {
        state: set() for state in model_inventory
    }

    # Group BLS programs by state for efficient lookup
    bls_by_state: dict[str, list[dict]] = {}
    for prog in bls_programs:
        state = prog.get("state", "Unknown")
        bls_by_state.setdefault(state, []).append(prog)

    # ── Pass 1: For each BLS program, find model match ────────────────────
    for bls_prog in bls_programs:
        state      = bls_prog.get("state", "Unknown")
        bls_name   = bls_prog.get("program_name", "")

        model_state = model_inventory.get(state, {})
        model_names = list(model_state.keys())

        match_result = fuzzy_match(bls_name, model_names, threshold)

        if match_result is None:
            # Scenario 2: On BLS, not in model
            new_candidates.append({
                "state":        state,
                "bls_name":     bls_name,
                "match_status": "new_candidate",
                "note":         "New program found on BLS Strategies. Sean to approve before adding to model.",
                "bls_record":   bls_prog,
                "match_score":  None,
            })
            log.debug(f"  [new_candidate] {state} / {bls_name}")

        else:
            matched_name, score = match_result
            matched_model_programs[state].add(matched_name)

            # Check for low confidence even though it's above threshold
            if score < 95:
                low_confidence.append({
                    "state":       state,
                    "bls_name":    bls_name,
                    "model_name":  matched_name,
                    "match_score": round(score, 1),
                    "note":        f"Fuzzy match confidence {score:.1f}% — Sean to confirm this is the same program.",
                })

            model_params = model_state[matched_name]

            # Compute parameter diffs
            diffs = compute_diff(model_params, bls_prog)

            # Scenario 3: Both present, parameters differ
            actionable_diffs = [d for d in diffs if d["diff_type"] == "value_changed"]
            if actionable_diffs:
                parameters_changed.append({
                    "state":        state,
                    "model_name":   matched_name,
                    "bls_name":     bls_name,
                    "match_status": "parameters_changed",
                    "match_score":  round(score, 1),
                    "diffs":        actionable_diffs,
                    "all_diffs":    diffs,
                    "bls_record":   bls_prog,
                    "note": (
                        "Program found in both model and BLS Strategies. "
                        "Parameter differences detected — Sean to review."
                    ),
                })
                log.debug(f"  [params_changed] {state} / {matched_name}: {len(actionable_diffs)} field(s) changed")
            else:
                # Active — no change
                active.append({
                    "state":        state,
                    "model_name":   matched_name,
                    "bls_name":     bls_name,
                    "match_status": "active",
                    "match_score":  round(score, 1),
                    "informational_diffs": [d for d in diffs if d["diff_type"] == "model_undocumented"],
                    "bls_record":   bls_prog,
                })
                log.debug(f"  [active] {state} / {matched_name}")

    # ── Pass 2: Model programs NOT matched → unverified ──────────────────
    for state, programs in model_inventory.items():
        for prog_name in programs:
            if prog_name not in matched_model_programs.get(state, set()):
                # Not found on BLS
                unverified.append({
                    "state":        state,
                    "model_name":   prog_name,
                    "match_status": "unverified",
                    "note": (
                        "Not found on BLS Strategies. "
                        "Possible sunset or page not yet covered — Sean to confirm."
                    ),
                })
                log.debug(f"  [unverified] {state} / {prog_name}")

    # ── Summary ───────────────────────────────────────────────────────────
    total_model = sum(len(v) for v in model_inventory.values())
    summary = {
        "run_at":                run_at,
        "total_programs_in_model": total_model,
        "total_programs_on_bls":   len(bls_programs),
        "states_scraped":          len(bls_by_state),
        "unverified":              len(unverified),
        "new_candidates":          len(new_candidates),
        "parameters_changed":      len(parameters_changed),
        "active":                  len(active),
        "low_confidence_matches":  len(low_confidence),
    }

    log.info("Detection complete:")
    for k, v in summary.items():
        if k != "run_at":
            log.info(f"  {k:<30} {v}")

    return {
        "run_at":                 run_at,
        "summary":                summary,
        "unverified":             unverified,
        "new_candidates":         new_candidates,
        "parameters_changed":     parameters_changed,
        "active":                 active,
        "low_confidence_matches": low_confidence,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(description="BLS Strategies Change Detection Engine")
    parser.add_argument(
        "--bls", metavar="PATH", default=str(DEFAULT_BLS_PATH),
        help=f"Path to bls_current.json (default: {DEFAULT_BLS_PATH})"
    )
    parser.add_argument(
        "--output", metavar="PATH", default=str(DEFAULT_OUTPUT_PATH),
        help=f"Output flagged JSON path (default: {DEFAULT_OUTPUT_PATH})"
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD, metavar="SCORE",
        help=f"Fuzzy match minimum confidence 0–100 (default: {DEFAULT_THRESHOLD})"
    )
    args = parser.parse_args()

    bls_path = Path(args.bls)
    if not bls_path.exists():
        log.error(f"BLS data file not found: {bls_path}")
        log.error("Run bls_scraper.py first to generate it.")
        sys.exit(1)

    with open(bls_path, encoding="utf-8") as f:
        bls_programs = json.load(f)
    log.info(f"Loaded {len(bls_programs)} programs from {bls_path}")

    model_inventory = load_model_inventory()

    flagged = run_detection(bls_programs, model_inventory, threshold=args.threshold)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(flagged, f, indent=2, ensure_ascii=False)
    log.info(f"Flagged output saved → {out_path}")
    print(f"\n✓ Flagged output saved to: {out_path}")


if __name__ == "__main__":
    main()
