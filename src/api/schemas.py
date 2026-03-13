"""
api/schemas.py — Request/response models for the EDai analyze endpoint.

Pydantic v2 is used when available (for FastAPI deployment).
Falls back to plain dataclasses when Pydantic is not installed, so the
orchestrator and memo_builder work in testing environments without FastAPI.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── Try Pydantic v2 ───────────────────────────────────────────────────────────
try:
    from pydantic import BaseModel, Field as PydanticField, field_validator, model_validator
    _PYDANTIC = True
except ImportError:
    _PYDANTIC = False


_VALID_ARCHETYPES = {"office", "manufacturing", "distribution"}
_VALID_USER_ROLES = {"business_leader", "site_selector", "econ_developer"}


# ─────────────────────────────────────────────────────────────────────────────
# Shared validation logic (used by both Pydantic and dataclass paths)
# ─────────────────────────────────────────────────────────────────────────────

def _validate_request_fields(
    archetype: str,
    headcount: int,
    avg_wage: float,
    capex: float,
    user_role: str,
) -> list[str]:
    """Return list of user-friendly error messages (empty = valid)."""
    errors = []
    if archetype.strip().lower() not in _VALID_ARCHETYPES:
        errors.append(f"archetype must be one of {sorted(_VALID_ARCHETYPES)}, got '{archetype}'")
    if user_role.strip().lower() not in _VALID_USER_ROLES:
        errors.append(f"user_role must be one of {sorted(_VALID_USER_ROLES)}, got '{user_role}'")
    if not (1 <= headcount <= 50_000):
        errors.append(f"headcount must be between 1 and 50,000, got {headcount}")
    if not (15_000 <= avg_wage <= 500_000):
        errors.append(f"avg_wage must be between $15,000 and $500,000, got {avg_wage}")
    if not (0 <= capex <= 50_000_000_000):
        errors.append(f"capex must be between $0 and $50,000,000,000, got {capex}")
    return errors


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC PATH  (FastAPI deployments)
# ─────────────────────────────────────────────────────────────────────────────

if _PYDANTIC:
    class AnalyzeRequest(BaseModel):
        archetype: str
        headcount: int
        avg_wage:  float
        capex:     float
        user_role: str
        state:     Optional[str] = None
        county:    Optional[str] = None

        @field_validator("archetype")
        @classmethod
        def _arch(cls, v):
            n = v.strip().lower()
            if n not in _VALID_ARCHETYPES:
                raise ValueError(f"archetype must be one of {sorted(_VALID_ARCHETYPES)}, got '{v}'")
            return n

        @field_validator("user_role")
        @classmethod
        def _role(cls, v):
            n = v.strip().lower()
            if n not in _VALID_USER_ROLES:
                raise ValueError(f"user_role must be one of {sorted(_VALID_USER_ROLES)}, got '{v}'")
            return n

        @field_validator("headcount")
        @classmethod
        def _hc(cls, v):
            if not (1 <= v <= 50_000):
                raise ValueError(f"headcount must be between 1 and 50,000, got {v}")
            return v

        @field_validator("avg_wage")
        @classmethod
        def _wage(cls, v):
            if not (15_000 <= v <= 500_000):
                raise ValueError(f"avg_wage must be between $15,000 and $500,000, got {v}")
            return v

        @field_validator("capex")
        @classmethod
        def _capex(cls, v):
            if not (0 <= v <= 50_000_000_000):
                raise ValueError(f"capex must be between $0 and $50,000,000,000, got {v}")
            return v

        @property
        def effective_state(self)  -> str: return self.state  or "Virginia"
        @property
        def effective_county(self) -> str: return self.county or "Richmond City"
        @property
        def state_is_placeholder(self)  -> bool: return not bool(self.state)
        @property
        def county_is_placeholder(self) -> bool: return not bool(self.county)

    class EngineResult(BaseModel):
        engine:     str
        status:     str
        data:       Dict[str, Any] = PydanticField(default_factory=dict)
        warnings:   List[str]     = PydanticField(default_factory=list)
        runtime_ms: float         = 0.0

    class AnalyzeResponse(BaseModel):
        request_id:   str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
        timestamp:    str = PydanticField(
            default_factory=lambda: datetime.now(timezone.utc).isoformat()
        )
        inputs:       AnalyzeRequest
        results:      Dict[str, EngineResult] = PydanticField(default_factory=dict)
        memo_context: Dict[str, Any]          = PydanticField(default_factory=dict)
        errors:       List[str]               = PydanticField(default_factory=list)

# ─────────────────────────────────────────────────────────────────────────────
# DATACLASS FALLBACK PATH  (testing / environments without Pydantic)
# ─────────────────────────────────────────────────────────────────────────────

else:
    @dataclass
    class AnalyzeRequest:  # type: ignore[no-redef]
        archetype: str
        headcount: int
        avg_wage:  float
        capex:     float
        user_role: str
        state:     Optional[str] = None
        county:    Optional[str] = None

        def __post_init__(self):
            self.archetype = self.archetype.strip().lower()
            self.user_role = self.user_role.strip().lower()
            errors = _validate_request_fields(
                self.archetype, self.headcount, self.avg_wage,
                self.capex, self.user_role,
            )
            if errors:
                raise ValueError("\n".join(errors))

        @property
        def effective_state(self)  -> str: return self.state  or "Virginia"
        @property
        def effective_county(self) -> str: return self.county or "Richmond City"
        @property
        def state_is_placeholder(self)  -> bool: return not bool(self.state)
        @property
        def county_is_placeholder(self) -> bool: return not bool(self.county)

    @dataclass
    class EngineResult:  # type: ignore[no-redef]
        engine:     str
        status:     str
        data:       Dict[str, Any] = field(default_factory=dict)
        warnings:   List[str]     = field(default_factory=list)
        runtime_ms: float         = 0.0

    @dataclass
    class AnalyzeResponse:  # type: ignore[no-redef]
        inputs:       AnalyzeRequest
        results:      Dict[str, EngineResult] = field(default_factory=dict)
        memo_context: Dict[str, Any]          = field(default_factory=dict)
        errors:       List[str]               = field(default_factory=list)
        request_id:   str = field(default_factory=lambda: str(uuid.uuid4()))
        timestamp:    str = field(
            default_factory=lambda: datetime.now(timezone.utc).isoformat()
        )
