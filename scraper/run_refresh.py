#!/usr/bin/env python3
"""
run_refresh.py — EDai Incentives Refresh Pipeline
==================================================
Orchestrates the three-step quarterly refresh in a single command:

  Step 1  bls_scraper.py      → data/bls_current.json
  Step 2  change_detector.py  → data/flagged.json
  Step 3  generate_report.py  → reports/bls_change_report_YYYYMMDD.{md,json}

Usage
-----
  # Full live run (requires internet):
  python scraper/run_refresh.py

  # Mock run — no network, uses built-in data:
  python scraper/run_refresh.py --mock

  # Specific states only (useful for spot-checks):
  python scraper/run_refresh.py --states alabama virginia

  # Skip scrape — re-use existing bls_current.json:
  python scraper/run_refresh.py --skip-scrape

  # Change detector fuzzy threshold:
  python scraper/run_refresh.py --threshold 85

Run from the project root:
  cd edai_accounting_modules
  python scraper/run_refresh.py
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Resolve paths (works whether run from root or scraper/) ─────────────────
_HERE = Path(__file__).parent
_ROOT = _HERE.parent
_DATA = _ROOT / "data"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("run_refresh")


# ---------------------------------------------------------------------------
# Import all three modules directly (avoids subprocess overhead + path issues)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

import scraper.bls_scraper      as bls_mod
import scraper.change_detector  as cd_mod
import scraper.generate_report  as rpt_mod


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def step1_scrape(
    states: list[str],
    mock: bool,
    delay: float,
    verbose: bool,
) -> list[dict]:
    """Run the BLS scraper and save data/bls_current.json."""
    log.info("═" * 60)
    log.info("STEP 1 — BLS Strategies Scrape")
    log.info("═" * 60)
    t0 = time.perf_counter()

    scraper = bls_mod.BLSScraper(delay=delay, verbose=verbose)

    if mock:
        log.info("Running in MOCK mode — no network requests")
        programs = bls_mod._build_mock_data(states, scraper.log)
    else:
        if not bls_mod.HAS_REQUESTS or not bls_mod.HAS_BS4:
            log.error(
                "Missing dependencies. Install: pip install requests beautifulsoup4 lxml\n"
                "Or re-run with --mock to test without a live scrape."
            )
            sys.exit(1)
        log.info(f"Scraping {len(states)} state(s)...")
        programs = scraper.scrape_states(states)

    scraper.print_summary(programs)
    out_path = scraper.save(programs)

    elapsed = time.perf_counter() - t0
    log.info(f"Step 1 complete in {elapsed:.1f}s — {len(programs)} programs scraped")
    return programs


def step2_detect(
    programs: list[dict],
    threshold: float,
) -> dict:
    """Run change detection and save data/flagged.json."""
    log.info("═" * 60)
    log.info("STEP 2 — Change Detection")
    log.info("═" * 60)
    t0 = time.perf_counter()

    model_inventory = cd_mod.load_model_inventory()
    flagged = cd_mod.run_detection(programs, model_inventory, threshold=threshold)

    flagged_path = _DATA / "flagged.json"
    flagged_path.parent.mkdir(parents=True, exist_ok=True)
    with open(flagged_path, "w", encoding="utf-8") as f:
        json.dump(flagged, f, indent=2, ensure_ascii=False)

    elapsed = time.perf_counter() - t0
    log.info(f"Step 2 complete in {elapsed:.1f}s → {flagged_path}")
    return flagged


def step3_report(flagged: dict) -> tuple[Path, Path]:
    """Generate markdown + JSON reports."""
    log.info("═" * 60)
    log.info("STEP 3 — Generate Change Report")
    log.info("═" * 60)
    t0 = time.perf_counter()

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    stamp    = now.strftime("%Y%m%d")

    out_dir   = _ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path   = out_dir / f"bls_change_report_{stamp}.md"
    json_path = out_dir / f"bls_change_report_{stamp}.json"

    md_content = rpt_mod.generate_markdown(flagged, date_str)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    report_json = {"generated_at": now.isoformat(), "date": date_str, **flagged}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2, ensure_ascii=False)

    elapsed = time.perf_counter() - t0
    log.info(f"Step 3 complete in {elapsed:.1f}s")
    log.info(f"  Markdown → {md_path}")
    log.info(f"  JSON     → {json_path}")

    return md_path, json_path


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_final_summary(
    programs: list[dict],
    flagged: dict,
    md_path: Path,
    json_path: Path,
    total_elapsed: float,
    mock: bool,
) -> None:
    s = flagged.get("summary", {})

    mode_tag = " [MOCK MODE]" if mock else ""
    print("\n" + "═" * 60)
    print(f"  EDai BLS Refresh Pipeline Complete{mode_tag}")
    print("═" * 60)
    print(f"  Total runtime:       {total_elapsed:.1f}s")
    print(f"  Programs scraped:    {len(programs)}")
    print(f"  States covered:      {s.get('states_scraped', 0)}")
    print("")
    print(f"  🔴 Unverified:       {s.get('unverified', 0):>3}   (possible sunset — Sean to confirm)")
    print(f"  🟡 New candidates:   {s.get('new_candidates', 0):>3}   (not in model — Sean to approve)")
    print(f"  🟠 Params changed:   {s.get('parameters_changed', 0):>3}   (diff detected — Sean to review)")
    print(f"  🟢 Active:           {s.get('active', 0):>3}   (no change)")
    if s.get("low_confidence_matches"):
        print(f"  ⚪ Low confidence:   {s.get('low_confidence_matches', 0):>3}   (manual review)")
    print("")
    print(f"  Reports:")
    print(f"    {md_path}")
    print(f"    {json_path}")
    print("═" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="EDai BLS Strategies Incentive Refresh Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--states", nargs="+", metavar="STATE",
        help="Specific states (default: all states in model database)"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use built-in mock data — no network required"
    )
    parser.add_argument(
        "--skip-scrape", action="store_true",
        help="Skip Step 1 and re-use existing data/bls_current.json"
    )
    parser.add_argument(
        "--threshold", type=float, default=90.0, metavar="SCORE",
        help="Fuzzy match confidence threshold 0–100 (default: 90)"
    )
    parser.add_argument(
        "--delay", type=float, default=bls_mod.REQUEST_DELAY, metavar="SECS",
        help=f"Seconds between HTTP requests (default: {bls_mod.REQUEST_DELAY})"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve state list
    if args.states:
        states = [s.title() for s in args.states]
    else:
        states = bls_mod._load_state_list()

    pipeline_start = time.perf_counter()

    # ── Step 1: Scrape ────────────────────────────────────────────────────
    if args.skip_scrape:
        bls_path = _DATA / "bls_current.json"
        if not bls_path.exists():
            log.error(f"--skip-scrape requested but {bls_path} not found. Run without --skip-scrape first.")
            sys.exit(1)
        with open(bls_path, encoding="utf-8") as f:
            programs = json.load(f)
        log.info(f"[skip-scrape] Loaded {len(programs)} programs from {bls_path}")
    else:
        programs = step1_scrape(states, mock=args.mock, delay=args.delay, verbose=args.verbose)

    # ── Step 2: Detect ────────────────────────────────────────────────────
    flagged = step2_detect(programs, threshold=args.threshold)

    # ── Step 3: Report ────────────────────────────────────────────────────
    md_path, json_path = step3_report(flagged)

    total_elapsed = time.perf_counter() - pipeline_start

    print_final_summary(programs, flagged, md_path, json_path, total_elapsed, args.mock)


if __name__ == "__main__":
    main()
