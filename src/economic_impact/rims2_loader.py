"""
RIMS II multiplier loader.

Loads state-level TypeII multiplier files from data/economic_impact/multipliers/.
Exposes get_multipliers(state) → RIMSMultiplierSet.

V1 PLACEHOLDER POLICY
─────────────────────
Only Virginia (VA) and North Carolina (NC) multipliers are available.
For any other state, Virginia multipliers are returned silently with a logged warning:

    WARNING: RIMS II multipliers not available for [STATE].
    Using Virginia multipliers as placeholder.
    Results are directionally correct but not state-specific.

This is a deliberate V1 design decision, not a bug.

ADDING A NEW STATE (no code changes required)
────────────────────────────────────────────
1. Obtain the RIMS II Type II multiplier set for the new state.
2. Export it in the same JSON schema as VA_TypeII.json:
       {"state": "TX", "tables": {"2-1_Output": {...}, ..., "2-5_TotMult": {...}}}
3. Drop the file at:
       data/economic_impact/multipliers/TX_TypeII.json
4. Restart the application (or call reload_multipliers()).
   The new state is automatically recognized on the next get_multipliers("Texas") call.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from .models import RIMSMultiplierSet

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# State name / abbreviation → 2-letter code
# ─────────────────────────────────────────────────────────────────────────────
_STATE_ALIASES: Dict[str, str] = {
    # Full names
    "virginia":       "VA",
    "north carolina": "NC",
    # Common abbreviations
    "va": "VA",
    "nc": "NC",
}


def _normalize_state(state: str) -> str:
    """Return upper-case 2-letter code for a state name/abbreviation, or the
    original string uppercased if not found in aliases."""
    return _STATE_ALIASES.get(state.strip().lower(), state.strip().upper())


# ─────────────────────────────────────────────────────────────────────────────
# Module-level cache  (loaded once at first call)
# ─────────────────────────────────────────────────────────────────────────────
_cache: Dict[str, RIMSMultiplierSet] = {}
_loaded: bool = False

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "economic_impact" / "multipliers"


def _parse_vintage(tables: dict) -> str:
    """Extract a human-readable vintage string from the TotMult meta block."""
    try:
        meta = tables["2-5_TotMult"]["meta"]
        return f"{meta.get('series', 'unknown series')}"
    except (KeyError, TypeError):
        return "unknown vintage"


def _load_all() -> None:
    """Scan the multipliers/ directory and load every *_TypeII.json file."""
    global _cache, _loaded

    if not _DATA_DIR.exists():
        logger.error("Multipliers directory not found: %s", _DATA_DIR)
        _loaded = True
        return

    for fp in sorted(_DATA_DIR.glob("*_TypeII.json")):
        state_code = fp.stem.split("_")[0].upper()   # "VA_TypeII" → "VA"
        try:
            with open(fp) as f:
                data = json.load(f)
            vintage = _parse_vintage(data.get("tables", {}))
            ms = RIMSMultiplierSet(
                state=state_code,
                tables=data.get("tables", {}),
                vintage=vintage,
                is_placeholder=False,
            )
            _cache[state_code] = ms
            logger.debug("Loaded RIMS II multipliers for %s (%s)", state_code, vintage)
        except Exception as exc:
            logger.error("Failed to load %s: %s", fp, exc)

    logger.info(
        "RIMS II loader: %d state(s) available: %s",
        len(_cache),
        ", ".join(sorted(_cache.keys())),
    )
    _loaded = True


def reload_multipliers() -> None:
    """Force a reload of all multiplier files (useful after dropping a new state file)."""
    global _cache, _loaded
    _cache = {}
    _loaded = False
    _load_all()


def _ensure_loaded() -> None:
    global _loaded
    if not _loaded:
        _load_all()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

_PLACEHOLDER_STATE = "VA"   # Virginia is the V1 default for unknown states


def get_multipliers(state: str) -> RIMSMultiplierSet:
    """Return the RIMS II Type II multiplier set for *state*.

    If state-specific multipliers are not available, returns Virginia multipliers
    with ``is_placeholder=True`` and logs a warning.

    Args:
        state: Full state name ("Virginia", "Texas") or 2-letter abbreviation ("VA", "TX").

    Returns:
        RIMSMultiplierSet for the requested state, or Virginia placeholder.
    """
    _ensure_loaded()

    code = _normalize_state(state)

    if code in _cache:
        return _cache[code]

    # ── Placeholder fallback ──────────────────────────────────────────────────
    logger.warning(
        "RIMS II multipliers not available for %s. "
        "Using Virginia multipliers as placeholder. "
        "Results are directionally correct but not state-specific.",
        state,
    )

    if _PLACEHOLDER_STATE not in _cache:
        raise RuntimeError(
            f"Virginia placeholder multipliers not found in {_DATA_DIR}. "
            "Ensure VA_TypeII.json is present."
        )

    va = _cache[_PLACEHOLDER_STATE]
    return RIMSMultiplierSet(
        state=_PLACEHOLDER_STATE,
        tables=va.tables,
        vintage=va.vintage,
        is_placeholder=True,
    )


def available_states() -> list[str]:
    """Return sorted list of state codes with loaded multipliers."""
    _ensure_loaded()
    return sorted(_cache.keys())
