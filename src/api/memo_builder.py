"""
api/memo_builder.py — Extracts key findings from a completed AnalyzeResponse
into a structured memo_context dict.

This dict is the input to Claude memo synthesis (Session J).  It distills
each engine's output into the facts a memo author needs, with no raw noise.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .schemas import AnalyzeResponse


def build_memo_context(response: "AnalyzeResponse") -> Dict[str, Any]:
    """
    Build a structured memo_context dict from a completed AnalyzeResponse.

    Keys
    ----
    user_role          : str — shapes memo framing
    archetype          : str
    inputs             : dict — echo of request inputs
    top_metros_codb    : list[dict] — top 10 ranked metros from CODB
    incentives_summary : dict — key incentives findings
    economic_impact    : dict — total jobs, earnings, output
    fiscal_impact      : dict — breakeven year, NPV, Year 1 revenues
    top_cities_scoring : list[dict] — top 10 cities from location scoring
    warnings           : list[str] — all engine warnings consolidated
    """
    request = response.inputs
    results = response.results

    # ── Consolidated warnings ─────────────────────────────────────────────────
    all_warnings: List[str] = list(response.errors)   # start with any engine failures
    for er in results.values():
        all_warnings.extend(er.warnings or [])

    # ── Inputs echo ──────────────────────────────────────────────────────────
    inputs_echo = {
        "archetype":    request.archetype,
        "headcount":    request.headcount,
        "avg_wage":     request.avg_wage,
        "capex":        request.capex,
        "state":        request.effective_state,
        "county":       request.effective_county,
        "state_is_placeholder":  request.state_is_placeholder,
        "county_is_placeholder": request.county_is_placeholder,
        "total_payroll": request.headcount * request.avg_wage,
    }

    # ── CODB ─────────────────────────────────────────────────────────────────
    codb_er = results.get("codb")
    if codb_er and codb_er.status == "success":
        codb_data = codb_er.data
        top_metros_codb = codb_data.get("top_metros", [])[:10]
        codb_summary = {
            "status":          "success",
            "archetype":       codb_data.get("archetype"),
            "metros_analyzed": codb_data.get("metros_total"),
            "avg_margin_pct":  codb_data.get("avg_margin_pct"),
            "best_metro":      top_metros_codb[0].get("metro") if top_metros_codb else None,
            "best_margin_pct": top_metros_codb[0].get("after_tax_margin") if top_metros_codb else None,
        }
    else:
        top_metros_codb = []
        codb_summary = {"status": "error", "error": (codb_er.data.get("error") if codb_er else "engine not run")}

    # ── Incentives ────────────────────────────────────────────────────────────
    inc_er = results.get("incentives")
    if inc_er and inc_er.status == "success":
        inc_data = inc_er.data
        incentives_summary = {
            "status":                "success",
            "state":                 inc_data.get("state"),
            "programs_eligible":     inc_data.get("programs_eligible"),
            "programs_evaluated":    inc_data.get("programs_evaluated"),
            "total_incentives_npv":  inc_data.get("total_incentives_npv"),
            "ebitx_margin":          inc_data.get("ebitx_margin"),
            "post_incentive_margin": inc_data.get("post_incentive_margin"),
            "top_programs":          inc_data.get("top_programs", [])[:5],
        }
    else:
        incentives_summary = {"status": "error", "error": (inc_er.data.get("error") if inc_er else "engine not run")}

    # ── Economic Impact ───────────────────────────────────────────────────────
    econ_er = results.get("economic_impact")
    if econ_er and econ_er.status == "success":
        econ_data = econ_er.data
        # Employment multiplier effect
        direct_jobs = request.headcount
        total_jobs  = econ_data.get("total_jobs", direct_jobs)
        multiplier  = round(total_jobs / direct_jobs, 2) if direct_jobs else None
        economic_impact = {
            "status":                "success",
            "state":                 econ_data.get("state"),
            "sector":                econ_data.get("sector"),
            "placeholder_used":      econ_data.get("placeholder_used"),
            "direct_jobs":           direct_jobs,
            "ops_total_jobs":        econ_data.get("ops_total_jobs"),
            "constr_total_jobs":     econ_data.get("constr_total_jobs"),
            "combined_total_jobs":   total_jobs,
            "jobs_multiplier":       multiplier,
            "ops_total_output":      econ_data.get("ops_total_output"),
            "ops_total_earnings":    econ_data.get("ops_total_earnings"),
            "ops_total_value_added": econ_data.get("ops_total_value_added"),
            "total_output":          econ_data.get("total_output"),
            "total_earnings":        econ_data.get("total_earnings"),
            "top_sectors":           econ_data.get("top_sectors", [])[:5],
        }
    else:
        economic_impact = {"status": "error", "error": (econ_er.data.get("error") if econ_er else "engine not run")}

    # ── Fiscal Impact ─────────────────────────────────────────────────────────
    fiscal_er = results.get("fiscal_impact")
    if fiscal_er and fiscal_er.status == "success":
        fd = fiscal_er.data
        fiscal_impact = {
            "status":                  "success",
            "state":                   fd.get("state"),
            "city":                    fd.get("city"),
            "project_type":            fd.get("project_type"),
            "y1_total_revenue":        fd.get("y1_total_revenue"),
            "y1_property_tax":         fd.get("y1_revenue_property"),
            "y1_sales_tax":            fd.get("y1_revenue_sales"),
            "y1_bpol":                 fd.get("y1_revenue_bpol"),
            "y1_pit":                  fd.get("y1_revenue_pit"),
            "y1_cit":                  fd.get("y1_revenue_cit"),
            "y1_utility":              fd.get("y1_revenue_utility"),
            "npv_10yr":                fd.get("npv_revenues"),
            "total_10yr_revenue":      fd.get("total_10yr_revenue"),
            "breakeven_project_year":  fd.get("breakeven_project_year"),
            "breakeven_calendar_year": fd.get("breakeven_calendar_year"),
            "property_tax_rate_pct":   fd.get("property_tax_rate_pct"),
            "sales_tax_rate_pct":      fd.get("sales_tax_rate_pct"),
        }
    else:
        fiscal_impact = {"status": "error", "error": (fiscal_er.data.get("error") if fiscal_er else "engine not run")}

    # ── Location Scoring ──────────────────────────────────────────────────────
    ls_er = results.get("location_scoring")
    if ls_er and ls_er.status == "success":
        ls_data = ls_er.data
        top_cities_scoring = [
            {
                "rank":        c["rank"],
                "city_state":  c["city_state"],
                "total_score": c["total_score"],
            }
            for c in ls_data.get("top_cities", [])[:10]
        ]
    else:
        top_cities_scoring = []

    # ── Memo framing hints by user_role ──────────────────────────────────────
    framing_hints = {
        "business_leader": (
            "Focus on ROI, incentive value, after-tax margin, and breakeven timeline. "
            "Avoid technical jargon. Emphasize competitive advantage and risk."
        ),
        "site_selector": (
            "Lead with metro rankings (CODB + location scoring). Emphasize labor market, "
            "real estate cost, and logistics. Provide data-dense comparison tables."
        ),
        "econ_developer": (
            "Lead with fiscal impact and economic multiplier effects. Quantify jobs created, "
            "tax revenues, and NPV to the jurisdiction. Include incentive programs available."
        ),
    }.get(request.user_role, "")

    # ── Assemble ──────────────────────────────────────────────────────────────
    return {
        "user_role":          request.user_role,
        "framing_hints":      framing_hints,
        "archetype":          request.archetype,
        "inputs":             inputs_echo,
        "top_metros_codb":    top_metros_codb,
        "codb_summary":       codb_summary,
        "incentives_summary": incentives_summary,
        "economic_impact":    economic_impact,
        "fiscal_impact":      fiscal_impact,
        "top_cities_scoring": top_cities_scoring,
        "warnings":           list(dict.fromkeys(all_warnings)),  # deduplicated, ordered
    }
