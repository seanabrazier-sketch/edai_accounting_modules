#!/usr/bin/env python3
"""
generate_report.py — BLS Change Report Generator
=================================================
Reads the flagged output from change_detector.py and produces:
  - reports/bls_change_report_YYYYMMDD.md   (human-readable markdown)
  - reports/bls_change_report_YYYYMMDD.json (programmatic use)

Usage
-----
  python scraper/generate_report.py
  python scraper/generate_report.py --input data/flagged.json
  python scraper/generate_report.py --output-dir reports/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_HERE    = Path(__file__).parent
_ROOT    = _HERE.parent
_DATA    = _ROOT / "data"
_REPORTS = _ROOT / "reports"

DEFAULT_FLAGGED_PATH = _DATA / "flagged.json"

log = logging.getLogger("generate_report")

# Comparable field labels for the diff table
FIELD_LABELS = {
    "jobs_threshold":    "Jobs threshold",
    "wage_threshold":    "Wage threshold ($)",
    "capex_threshold":   "Capex threshold ($)",
    "credit_rate":       "Credit rate",
    "award_cap":         "Award cap ($)",
    "carryforward_years": "Carryforward (years)",
    "refundable":        "Refundable?",
}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_val(v: Any, field: str = "") -> str:
    """Human-friendly value formatting."""
    if v is None:
        return "—"
    if v == "not documented":
        return "*(not documented)*"
    if field == "credit_rate" and isinstance(v, float):
        return f"{v * 100:.1f}%"
    if field in ("wage_threshold", "capex_threshold", "award_cap") and isinstance(v, (int, float)):
        return f"${v:,.0f}"
    if field == "refundable":
        return "Yes" if v else "No"
    return str(v)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a Markdown table string."""
    sep = " | ".join("---" for _ in headers)
    header_row = " | ".join(headers)
    lines = [f"| {header_row} |", f"| {sep} |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _count_label(n: int, singular: str, plural: Optional[str] = None) -> str:
    label = plural if (plural and n != 1) else singular
    return f"{n} {label}"


# ---------------------------------------------------------------------------
# Report section builders
# ---------------------------------------------------------------------------

def _section_summary(summary: dict) -> str:
    lines = ["## Summary\n"]
    lines.append(f"- Total programs in model: **{summary.get('total_programs_in_model', 0)}**")
    lines.append(f"- Total programs on BLS Strategies: **{summary.get('total_programs_on_bls', 0)}**")
    lines.append(f"- States scraped: **{summary.get('states_scraped', 0)}**")
    lines.append("")
    lines.append(f"| Status | Count |")
    lines.append(f"| --- | --- |")
    lines.append(f"| 🔴 Unverified (possible sunset) | **{summary.get('unverified', 0)}** |")
    lines.append(f"| 🟡 New candidates (not in model) | **{summary.get('new_candidates', 0)}** |")
    lines.append(f"| 🟠 Parameters changed | **{summary.get('parameters_changed', 0)}** |")
    lines.append(f"| 🟢 Active (no change) | **{summary.get('active', 0)}** |")
    lines.append(f"| ⚪ Low-confidence matches (manual review) | **{summary.get('low_confidence_matches', 0)}** |")
    return "\n".join(lines)


def _section_unverified(items: list[dict]) -> str:
    if not items:
        return "## 🔴 Unverified Programs (Sean to confirm sunset)\n\n*None — all model programs found on BLS.*\n"

    lines = [
        "## 🔴 Unverified Programs (Sean to confirm sunset)\n",
        f"These **{len(items)}** programs are in the model but were **not found** on BLS Strategies.",
        "They may have been sunsetted, renamed, or may not yet have a BLS page.",
        "Sean to confirm status before removing from model.\n",
    ]

    rows = [[item["state"], item["model_name"], item["note"]] for item in items]
    lines.append(_md_table(["State", "Program Name", "Note"], rows))
    return "\n".join(lines)


def _section_new_candidates(items: list[dict]) -> str:
    if not items:
        return "## 🟡 New Candidates (Sean to approve)\n\n*None — no new programs found on BLS.*\n"

    lines = [
        "## 🟡 New Candidates (Sean to approve)\n",
        f"These **{len(items)}** programs were found on BLS Strategies but are **not in the model**.",
        "Sean to approve before adding to the model.\n",
    ]

    rows = []
    for item in items:
        r = item.get("bls_record", {})
        rows.append([
            item["state"],
            item["bls_name"],
            r.get("program_type") or "—",
            _fmt_val(r.get("jobs_threshold"), "jobs_threshold"),
            _fmt_val(r.get("wage_threshold"), "wage_threshold"),
            _fmt_val(r.get("capex_threshold"), "capex_threshold"),
            _fmt_val(r.get("credit_rate"), "credit_rate"),
            _fmt_val(r.get("award_cap"), "award_cap"),
            _fmt_val(r.get("carryforward_years"), "carryforward_years"),
            _fmt_val(r.get("refundable"), "refundable"),
            r.get("program_status") or "—",
        ])

    lines.append(_md_table(
        ["State", "Program Name", "Type", "Jobs Min", "Wage Min",
         "Capex Min", "Credit Rate", "Award Cap", "Carryforward", "Refundable", "Status"],
        rows,
    ))
    return "\n".join(lines)


def _section_parameters_changed(items: list[dict]) -> str:
    if not items:
        return "## 🟠 Parameters Changed (Sean to review diffs)\n\n*None — no parameter changes detected.*\n"

    lines = [
        "## 🟠 Parameters Changed (Sean to review diffs)\n",
        f"These **{len(items)}** programs exist in both the model and BLS Strategies "
        "but have **detected parameter differences**. Sean to review and update model if correct.\n",
    ]

    for item in items:
        state      = item.get("state", "?")
        model_name = item.get("model_name", "?")
        bls_name   = item.get("bls_name", "?")
        score      = item.get("match_score")
        diffs      = item.get("diffs", [])

        lines.append(f"### {state} — {model_name}")
        if model_name != bls_name:
            lines.append(f"> *BLS name: \"{bls_name}\"* (match confidence: {score}%)")
        elif score is not None:
            lines.append(f"> Match confidence: {score}%")
        lines.append("")

        # Diff table
        diff_rows = []
        for d in diffs:
            field  = d.get("field", "")
            label  = FIELD_LABELS.get(field, field)
            m_val  = _fmt_val(d.get("model_value"), field)
            b_val  = _fmt_val(d.get("bls_value"), field)
            change = "⚠️ Changed" if d.get("diff_type") == "value_changed" else "ℹ️ BLS only"
            diff_rows.append([label, m_val, b_val, change])

        lines.append(_md_table(["Field", "Model Value", "BLS Value", "Status"], diff_rows))
        lines.append("")

    return "\n".join(lines)


def _section_active(items: list[dict]) -> str:
    if not items:
        return "## 🟢 Active Programs (No Change)\n\n*None.*\n"

    lines = [
        "## 🟢 Active Programs (No Change)\n",
        f"These **{len(items)}** programs are confirmed active with no detected parameter changes.\n",
    ]

    rows = []
    for item in items:
        info_diffs = item.get("informational_diffs", [])
        info_note  = f"{len(info_diffs)} undocumented field(s)" if info_diffs else ""
        rows.append([
            item.get("state", "?"),
            item.get("model_name", "?"),
            f"{item.get('match_score', 100):.0f}%",
            info_note,
        ])

    lines.append(_md_table(["State", "Program Name", "BLS Match %", "Notes"], rows))
    return "\n".join(lines)


def _section_low_confidence(items: list[dict]) -> str:
    if not items:
        return ""

    lines = [
        "## ⚪ Low-Confidence Matches (Manual Review)\n",
        f"These **{len(items)}** matches have confidence below 95% — Sean to confirm "
        "the model program and BLS program are the same.\n",
    ]

    rows = []
    for item in items:
        rows.append([
            item.get("state", "?"),
            item.get("model_name", "?"),
            item.get("bls_name", "?"),
            f"{item.get('match_score', 0):.1f}%",
        ])

    lines.append(_md_table(
        ["State", "Model Name", "BLS Name", "Confidence"],
        rows,
    ))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def generate_markdown(flagged: dict, date_str: str) -> str:
    summary     = flagged.get("summary", {})
    run_at      = flagged.get("run_at", "unknown")
    unverified  = flagged.get("unverified", [])
    new_cands   = flagged.get("new_candidates", [])
    changed     = flagged.get("parameters_changed", [])
    active      = flagged.get("active", [])
    low_conf    = flagged.get("low_confidence_matches", [])

    sections = [
        f"# BLS Strategies Change Report — {date_str}",
        "",
        f"> Generated: {run_at}  ",
        f"> Model programs: {summary.get('total_programs_in_model', 0)} | "
        f"BLS programs: {summary.get('total_programs_on_bls', 0)} | "
        f"States scraped: {summary.get('states_scraped', 0)}",
        "",
        "---",
        "",
        _section_summary(summary),
        "",
        "---",
        "",
        _section_unverified(unverified),
        "",
        "---",
        "",
        _section_new_candidates(new_cands),
        "",
        "---",
        "",
        _section_parameters_changed(changed),
        "",
        "---",
        "",
        _section_active(active),
    ]

    # Low confidence section only if there are items
    if low_conf:
        sections += ["", "---", "", _section_low_confidence(low_conf)]

    sections += [
        "",
        "---",
        "",
        "*This report is generated automatically by the EDai incentives refresh pipeline.*  ",
        "*All flagged items require Sean's review before any model updates are made.*",
    ]

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(description="BLS Change Report Generator")
    parser.add_argument(
        "--input", metavar="PATH", default=str(DEFAULT_FLAGGED_PATH),
        help=f"Flagged JSON from change_detector (default: {DEFAULT_FLAGGED_PATH})"
    )
    parser.add_argument(
        "--output-dir", metavar="DIR", default=str(_REPORTS),
        help=f"Directory for report output (default: {_REPORTS})"
    )
    args = parser.parse_args()

    flagged_path = Path(args.input)
    if not flagged_path.exists():
        log.error(f"Flagged data not found: {flagged_path}")
        log.error("Run change_detector.py first.")
        sys.exit(1)

    with open(flagged_path, encoding="utf-8") as f:
        flagged = json.load(f)

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    stamp    = now.strftime("%Y%m%d")

    out_dir  = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path   = out_dir / f"bls_change_report_{stamp}.md"
    json_path = out_dir / f"bls_change_report_{stamp}.json"

    # Markdown report
    md_content = generate_markdown(flagged, date_str)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    log.info(f"Markdown report → {md_path}")

    # JSON report (same flagged data with metadata)
    report_json = {
        "generated_at": now.isoformat(),
        "date":         date_str,
        **flagged,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2, ensure_ascii=False)
    log.info(f"JSON report    → {json_path}")

    summary = flagged.get("summary", {})
    print(f"\n✓ Reports generated:")
    print(f"    {md_path}")
    print(f"    {json_path}")
    print(f"\n  Summary:")
    print(f"    Unverified:          {summary.get('unverified', 0)}")
    print(f"    New candidates:      {summary.get('new_candidates', 0)}")
    print(f"    Parameters changed:  {summary.get('parameters_changed', 0)}")
    print(f"    Active (no change):  {summary.get('active', 0)}")

    return md_path, json_path


if __name__ == "__main__":
    main()
