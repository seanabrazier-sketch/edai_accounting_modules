"""
api/main.py — EDai Location Intelligence FastAPI application.

Endpoints
---------
GET  /health      — liveness check
POST /analyze     — run all five engines from a single intake form
GET  /metros      — list available metros from CODB engine
GET  /variables   — location scoring variable list and default weights

V1 design constraints:
  • No authentication, no user accounts — fully public
  • CORS: allow all origins
  • Engine failures are isolated; one bad engine never crashes the request
  • Virginia / Richmond City used as placeholders when state/county are omitted

Run with:
    cd edai_accounting_modules
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .orchestrator import run_all_engines
from .schemas import AnalyzeRequest, AnalyzeResponse

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="EDai Location Intelligence API",
    description=(
        "Single-intake analysis endpoint that runs five engines in parallel: "
        "Incentives, Metro CODB, Economic Impact, Location Scoring, and Fiscal Impact."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for V1 (public tool, no auth)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Custom validation error handler — user-friendly messages, not raw Pydantic
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Return clear, user-friendly error messages instead of raw Pydantic output."""
    messages: List[str] = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"]) if error["loc"] else "body"
        msg   = error["msg"]
        messages.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=422,
        content={
            "error":   "Validation failed",
            "details": messages,
            "hint":    "Check the /docs endpoint for field descriptions and valid values.",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Liveness check")
async def health_check() -> Dict[str, Any]:
    """
    Returns 200 OK with engine list.
    Use this to verify the API is running before submitting an analysis.
    """
    return {
        "status":  "ok",
        "version": "1.0.0",
        "engines": [
            "incentives",
            "codb",
            "economic_impact",
            "location_scoring",
            "fiscal_impact",
        ],
    }


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Run all five engines from a single intake form",
    response_description="Unified analysis result with per-engine status and memo context",
)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run all five location intelligence engines in parallel.

    **Inputs:**  archetype, headcount, avg_wage, capex, user_role, and optionally state/county.

    **Outputs:**  Per-engine results plus a structured memo_context ready for Claude synthesis.

    **Engine failures** are isolated — if any single engine errors, the others still complete
    and the failed engine's EngineResult will have `status: "error"` with the message in `data.error`.
    The list of any engine errors appears in the top-level `errors` field.

    **Placeholders:**  If `state` is omitted, Virginia is used as a placeholder (flagged in warnings).
    If `county` is omitted, Richmond City is used.
    """
    try:
        response = run_all_engines(request)
        return response
    except Exception as exc:
        logger.exception("Unexpected error in /analyze")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/metros",
    summary="List available metros from the CODB engine",
)
async def get_metros(archetype: Optional[str] = "office") -> Dict[str, Any]:
    """
    Return all metros available in the CODB (Cost of Doing Business) engine,
    optionally pre-ranked for a given archetype.

    Query params:
    - `archetype`: one of `office` | `manufacturing` | `distribution` (default: `office`)
    """
    _valid = {"office", "manufacturing", "distribution"}
    arch = (archetype or "office").lower()
    if arch not in _valid:
        raise HTTPException(
            status_code=400,
            detail=f"archetype must be one of {sorted(_valid)}, got '{archetype}'"
        )
    try:
        from ..metro_codb.codb_model import run_archetype, summary_table
        results = run_archetype(arch)
        rows = summary_table(results)
        return {
            "archetype":     arch,
            "metros_count":  len(rows),
            "metros":        rows,
        }
    except Exception as exc:
        logger.exception("Error in /metros")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/memo",
    summary="Generate a Claude-powered decision memo",
)
async def generate_memo(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call the Claude API to synthesize engine results into a location decision memo.

    Request body:
    - `memo_context`: the structured dict from /analyze → memo_context
    - `user_role`: one of business_leader | site_selector | econ_developer

    Returns:
    - `memo`: the full memo text
    - `model`: the Claude model used

    Requires ANTHROPIC_API_KEY env var to be set.
    """
    import os
    import json
    import requests as _requests

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY environment variable is not set on the server. "
                   "Set it and restart the API to enable memo generation."
        )

    memo_context = body.get("memo_context", {})
    user_role    = body.get("user_role", "business_leader")

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    system_prompt = (
        "You are an expert economic development analyst writing a location decision memo. "
        "Your writing is direct, data-driven, and professionally authoritative. "
        "You write for sophisticated readers — no hedging, no filler. Every sentence earns its place.\n\n"
        "Memo structure (always follow this exactly):\n"
        "1. EXECUTIVE SUMMARY — 2-3 sentences max, lead with the answer\n"
        "2. COST COMPETITIVENESS — cite actual margins and dollar differences\n"
        "3. TALENT & LOCATION PROFILE — cite scores, pool sizes, growth rates\n"
        "4. INCENTIVES CONTEXT — cite actual NPV numbers and program names\n"
        "5. ECONOMIC & FISCAL PICTURE — cite jobs, output, fiscal revenue, breakeven\n"
        "6. RECOMMENDED SHORTLIST — ranked #1, #2, #3 with one-line rationale each\n"
        "7. WHAT TO WATCH — exactly 3 risks or caveats, numbered\n\n"
        "Tone by user_role:\n"
        "- business_leader: bottom-line impact, execution risk, ROI\n"
        "- site_selector: comparative analysis, client recommendation framing\n"
        "- econ_developer: community ROI, fiscal returns, incentive negotiation context\n\n"
        "CRITICAL: Be specific. Cite actual numbers from the data. No placeholder text. "
        "If data is missing for a section, skip it gracefully rather than using generic language."
    )

    user_prompt = (
        f"Write a complete location decision memo based on this analysis:\n\n"
        f"{json.dumps(memo_context, indent=2, default=str)}\n\n"
        f"User role: {user_role}\n\n"
        "Write the full memo now. Use the exact section structure above. "
        "Cite specific numbers — metros, margins, NPVs, job counts, fiscal revenues. "
        "Do not use placeholder text or hedging language. Lead with conclusions."
    )

    model = "claude-opus-4-6"
    payload = {
        "model":      model,
        "max_tokens": 2048,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_prompt}],
    }
    headers = {
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }

    try:
        resp = _requests.post(
            f"{base_url}/v1/messages",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        memo_text = data["content"][0]["text"]
        return {"memo": memo_text, "model": model}
    except _requests.HTTPError as exc:
        detail = f"Claude API error {exc.response.status_code}: {exc.response.text[:400]}"
        logger.error(detail)
        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception as exc:
        logger.exception("Error calling Claude API")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/variables",
    summary="List location scoring variables and default weights",
)
async def get_variables(archetype: Optional[str] = None) -> Dict[str, Any]:
    """
    Return the full list of location scoring variables with metadata.

    Query params:
    - `archetype`: if provided, also return the archetype-specific weight config.
      One of `office` | `manufacturing` | `distribution`.
    """
    try:
        from ..location_scoring.data_loader import get_categories, get_variable_specs
        specs = get_variable_specs()
        cats  = get_categories()

        variables = [
            {
                "name":             s.name,
                "plain_name":       s.plain_name,
                "category":         s.category,
                "higher_is_better": s.higher_is_better,
                "log_transform":    s.log_transform,
                "geographic_level": s.geographic_level,
                "data_source":      s.data_source,
                "default_weight":   s.default_weight,
            }
            for s in specs
        ]

        result: Dict[str, Any] = {
            "variable_count": len(variables),
            "categories":     cats,
            "variables":      variables,
        }

        if archetype:
            from .input_mappers import get_default_weights_for_archetype
            arch = archetype.lower()
            config = get_default_weights_for_archetype(arch)
            if config:
                result["archetype_weights"] = {
                    "archetype":  arch,
                    "weights":    config.weights,
                    "total":      round(config.total(), 2),
                }

        return result

    except Exception as exc:
        logger.exception("Error in /variables")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
