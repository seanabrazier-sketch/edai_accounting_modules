"""
location_scoring/models.py
Data models for the EDai Location Scoring engine.

Variable specs are derived from the September 2022 Common House master dataset
(WalletHub 181-city "Foodie Cities" universe). Direction flags and log-transform
flags were inferred from domain knowledge; weights default to equal and are
normalized to 100 at scoring time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Variable specification ───────────────────────────────────────────────────

@dataclass
class VariableSpec:
    """
    Configuration for one scoring variable.

    Attributes
    ----------
    name : str
        Column name as it appears in city_data.json raw_values dict.
    plain_name : str | None
        Human-readable description from the Excel header rows.
    category : str
        Top-level grouping (e.g. "Demographics", "Real estate", "Hotel").
    geographic_level : str | None
        Geographic grain at which this variable was collected
        (e.g. "Zip code", "Metro area", "County").
    data_source : str | None
        Original data provider (e.g. "ACS 2016-2020", "CoStar").
    vintage_date : str
        Approximate data vintage (e.g. "September 2022").
    higher_is_better : bool
        True  → highest raw value earns score 5.
        False → lowest raw value earns score 5.
    log_transform : bool
        True → apply ln(x + 1) before min-max scaling.
        Used for wide-range variables (population, job counts) to
        prevent a handful of large cities from dominating the scale.
    default_weight : float
        Relative weight for this variable.  All variables start at 1.0;
        ScoringConfig.normalize() converts them to percentages summing to 100.
    """
    name: str
    category: str
    higher_is_better: bool
    log_transform: bool
    default_weight: float = 1.0
    plain_name: Optional[str] = None
    geographic_level: Optional[str] = None
    data_source: Optional[str] = None
    vintage_date: str = "September 2022"

    @classmethod
    def from_dict(cls, d: dict) -> "VariableSpec":
        return cls(
            name=d["name"],
            category=d["category"],
            higher_is_better=d["higher_is_better"],
            log_transform=d["log_transform"],
            default_weight=d.get("default_weight", 1.0),
            plain_name=d.get("plain_name"),
            geographic_level=d.get("geographic_level"),
            data_source=d.get("data_source"),
            vintage_date=d.get("vintage_date", "September 2022"),
        )


# ── City record ──────────────────────────────────────────────────────────────

@dataclass
class CityRecord:
    """
    One city with its raw variable values and (optionally) computed scores.

    Attributes
    ----------
    city_name : str
        City name only (e.g. "Portland").
    state : str
        Full state name (e.g. "Oregon").
    city_state : str
        Original combined key from the dataset (e.g. "Portland, Oregon").
    metro : str | None
        EMSI metro area string (e.g. "Portland-Vancouver-Hillsboro, OR-WA Metro Area").
    raw_values : dict
        Mapping of variable_name → raw float value.
        Missing variables are filled with the cross-city median at scoring time.
    scores : dict
        Mapping of variable_name → 1–5 scalar score (populated after scoring).
    """
    city_name: str
    state: str
    city_state: str
    metro: Optional[str] = None
    raw_values: Dict[str, float] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "CityRecord":
        city_state = d.get("city_state", "")
        # Split "Portland, Oregon" → ("Portland", "Oregon")
        parts = [p.strip() for p in city_state.split(",", 1)]
        city_name = parts[0] if parts else city_state
        state = parts[1] if len(parts) > 1 else ""
        return cls(
            city_name=city_name,
            state=state,
            city_state=city_state,
            metro=d.get("emsi_area"),
            raw_values={
                k: float(v) for k, v in d.get("raw_values", {}).items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            },
        )


# ── Scoring configuration ────────────────────────────────────────────────────

@dataclass
class ScoringConfig:
    """
    User-supplied weight configuration.

    Weights do not need to sum to 100 on input — call normalize() to
    convert them to percentages before passing to the scoring engine.

    Attributes
    ----------
    weights : dict
        Mapping of variable_name → weight (any positive float).
    """
    weights: Dict[str, float] = field(default_factory=dict)

    def normalize(self) -> "ScoringConfig":
        """
        Return a new ScoringConfig where weights sum exactly to 100.
        Zero-weight variables remain zero.  Raises ValueError if all weights
        are zero or negative.
        """
        total = sum(w for w in self.weights.values() if w > 0)
        if total <= 0:
            raise ValueError("ScoringConfig: all weights are zero or negative.")
        normalized = {k: (v / total) * 100.0 for k, v in self.weights.items()}
        return ScoringConfig(weights=normalized)

    def total(self) -> float:
        return sum(self.weights.values())

    @classmethod
    def equal_weights(cls, variable_names: List[str]) -> "ScoringConfig":
        """
        Create equal-weight config for the given variable list.
        Each variable gets weight = 100 / N after normalization.
        """
        w = {name: 1.0 for name in variable_names}
        config = cls(weights=w)
        return config.normalize()


# ── Scoring result ───────────────────────────────────────────────────────────

@dataclass
class ScoringResult:
    """
    Final scoring output for one city.

    Attributes
    ----------
    city_name : str
    state : str
    city_state : str
    metro : str | None
    total_score : float
        Sum of all weighted variable scores (1–5 scale each, weighted to 100).
    category_scores : dict
        Mapping of category_name → sum of weighted scores within that category.
    variable_scores : dict
        Mapping of variable_name → weighted scalar score (pre-summed per variable).
    rank : int
        1-based rank among all scored cities (1 = best).
    missing_vars : list
        Variables for which the city was missing a raw value (median was substituted).
    """
    city_name: str
    state: str
    city_state: str
    total_score: float
    category_scores: Dict[str, float]
    variable_scores: Dict[str, float]
    rank: int = 0
    metro: Optional[str] = None
    missing_vars: List[str] = field(default_factory=list)
