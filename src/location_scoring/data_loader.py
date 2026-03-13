"""
location_scoring/data_loader.py
Loads and caches variable specs and city data from the extracted JSON files.

# TODO: Replace WalletHub 181-city universe with EDai 100-metro CODB universe
# in a future data refresh session. Current data vintage: September 2022.
# Apartment rents and home prices are particularly stale by 2026.
"""
from __future__ import annotations

import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from .models import CityRecord, ScoringConfig, VariableSpec

logger = logging.getLogger(__name__)

# Data directory: two levels up from this file (src/location_scoring → repo root → data/)
_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "location_scoring"

_VARIABLE_SPECS_FILE = _DATA_DIR / "variable_specs.json"
_CITY_DATA_FILE      = _DATA_DIR / "city_data.json"
_CROSSWALKS_FILE     = _DATA_DIR / "crosswalks.json"

# Module-level cache (populated on first call)
_specs_cache:  Optional[List[VariableSpec]] = None
_cities_cache: Optional[List[CityRecord]]   = None


# ── Internal loaders ────────────────────────────────────────────────────────

def _load_specs() -> List[VariableSpec]:
    global _specs_cache
    if _specs_cache is not None:
        return _specs_cache

    if not _VARIABLE_SPECS_FILE.exists():
        raise FileNotFoundError(
            f"variable_specs.json not found at {_VARIABLE_SPECS_FILE}. "
            "Run the Part 1 extraction script first."
        )

    with open(_VARIABLE_SPECS_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    _specs_cache = [VariableSpec.from_dict(d) for d in raw]
    logger.info("Loaded %d variable specs from %s", len(_specs_cache), _VARIABLE_SPECS_FILE)
    return _specs_cache


def _load_cities(specs: List[VariableSpec]) -> List[CityRecord]:
    """
    Load city records.  Missing numeric values are logged as warnings;
    the scoring engine will substitute medians at runtime.
    """
    global _cities_cache
    if _cities_cache is not None:
        return _cities_cache

    if not _CITY_DATA_FILE.exists():
        raise FileNotFoundError(
            f"city_data.json not found at {_CITY_DATA_FILE}. "
            "Run the Part 1 extraction script first."
        )

    with open(_CITY_DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    cities = [CityRecord.from_dict(d) for d in raw]

    # Warn on missing variables (scoring engine will impute at runtime)
    spec_names = {s.name for s in specs}
    missing_count = 0
    for city in cities:
        city_vars = set(city.raw_values.keys())
        missing = spec_names - city_vars
        if missing:
            missing_count += len(missing)
            logger.debug(
                "City '%s' missing %d variable(s): %s",
                city.city_state, len(missing), sorted(missing)[:5],
            )

    if missing_count:
        logger.warning(
            "Total missing variable slots across all cities: %d "
            "(will be imputed with cross-city medians at scoring time)",
            missing_count,
        )

    logger.info("Loaded %d city records from %s", len(cities), _CITY_DATA_FILE)
    _cities_cache = cities
    return _cities_cache


# ── Public API ───────────────────────────────────────────────────────────────

def get_variable_specs() -> List[VariableSpec]:
    """Return all 147 variable specifications."""
    return _load_specs()


def get_all_cities() -> List[CityRecord]:
    """Return all 181 city records with raw_values populated."""
    specs = _load_specs()
    return _load_cities(specs)


def get_default_weights() -> ScoringConfig:
    """
    Return equal-weight ScoringConfig (weights normalized to sum to 100).
    All variables receive weight = 100 / N.
    """
    specs = get_variable_specs()
    var_names = [s.name for s in specs]
    config = ScoringConfig.equal_weights(var_names)
    logger.info(
        "Default equal weights: %.4f per variable (%d variables, sum=%.2f)",
        100.0 / len(var_names), len(var_names), config.total(),
    )
    return config


def get_categories() -> List[str]:
    """Return unique category names in the order they first appear in variable_specs."""
    specs = get_variable_specs()
    seen = []
    for s in specs:
        if s.category not in seen:
            seen.append(s.category)
    return seen


def get_specs_by_category() -> Dict[str, List[VariableSpec]]:
    """Return dict of category → list of VariableSpec."""
    specs = get_variable_specs()
    result: Dict[str, List[VariableSpec]] = {}
    for s in specs:
        result.setdefault(s.category, []).append(s)
    return result


def clear_cache() -> None:
    """
    Evict the in-memory caches.  Call this if the JSON files are updated
    and you need to reload without restarting the process.
    """
    global _specs_cache, _cities_cache
    _specs_cache = None
    _cities_cache = None
    logger.info("data_loader cache cleared.")
