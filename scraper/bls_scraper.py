#!/usr/bin/env python3
"""
bls_scraper.py — BLS Strategies Incentive Scraper
==================================================
Crawls https://www.blsstrategies.com/incentives/[state] for each state
in the program database and extracts incentive program data.

Usage
-----
  # Full scrape — all states in model:
  python scraper/bls_scraper.py

  # Specific states only (checkpoint / spot-check):
  python scraper/bls_scraper.py --states alabama virginia

  # Use built-in mock data (no network required — for CI/testing):
  python scraper/bls_scraper.py --mock

  # Scrape + show output without saving:
  python scraper/bls_scraper.py --dry-run

Network note
------------
This script makes outbound HTTPS requests to blsstrategies.com.
It must be run from a machine with public internet access (e.g. Sean's
Windows workstation).  Running from an environment with an egress proxy
will result in 403 / tunnel errors — use --mock in that case.

Requirements
------------
  pip install requests beautifulsoup4 lxml

Output
------
  data/bls_current.json  — array of program objects, one per scraped program
  scraper/bls_scraper.log
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Optional imports — fail gracefully with useful error messages
# ---------------------------------------------------------------------------
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry          # type: ignore
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup                 # type: ignore
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE   = Path(__file__).parent
_ROOT   = _HERE.parent
_DATA   = _ROOT / "data"
_LOG    = _HERE / "bls_scraper.log"
_PROGRAMS_TXT = _ROOT / "src" / "accounting" / "incentive_programs.txt"

BASE_URL = "https://www.blsstrategies.com/incentives"

# Seconds to sleep between requests (be a good citizen)
REQUEST_DELAY = 1.5

# ---------------------------------------------------------------------------
# State → URL-slug mapping
# ---------------------------------------------------------------------------
STATE_SLUGS: dict[str, str] = {
    "Alabama":        "alabama",
    "Arizona":        "arizona",
    "Arkansas":       "arkansas",
    "California":     "california",
    "Colorado":       "colorado",
    "Connecticut":    "connecticut",
    "Delaware":       "delaware",
    "Florida":        "florida",
    "Georgia":        "georgia",
    "Idaho":          "idaho",
    "Illinois":       "illinois",
    "Indiana":        "indiana",
    "Iowa":           "iowa",
    "Kansas":         "kansas",
    "Kentucky":       "kentucky",
    "Louisiana":      "louisiana",
    "Maine":          "maine",
    "Maryland":       "maryland",
    "Massachusetts":  "massachusetts",
    "Michigan":       "michigan",
    "Minnesota":      "minnesota",
    "Mississippi":    "mississippi",
    "Missouri":       "missouri",
    "Montana":        "montana",
    "Nebraska":       "nebraska",
    "Nevada":         "nevada",
    "New Hampshire":  "new-hampshire",
    "New Jersey":     "new-jersey",
    "New Mexico":     "new-mexico",
    "New York":       "new-york",
    "North Carolina": "north-carolina",
    "North Dakota":   "north-dakota",
    "Ohio":           "ohio",
    "Oklahoma":       "oklahoma",
    "Oregon":         "oregon",
    "Pennsylvania":   "pennsylvania",
    "Rhode Island":   "rhode-island",
    "South Carolina": "south-carolina",
    "South Dakota":   "south-dakota",
    "Tennessee":      "tennessee",
    "Texas":          "texas",
    "Utah":           "utah",
    "Vermont":        "vermont",
    "Virginia":       "virginia",
    "Washington":     "washington",
    "West Virginia":  "west-virginia",
    "Wisconsin":      "wisconsin",
    "Wyoming":        "wyoming",
}


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def _setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(_LOG, encoding="utf-8"),
        ],
    )
    return logging.getLogger("bls_scraper")


# ---------------------------------------------------------------------------
# HTTP session with retry
# ---------------------------------------------------------------------------
def _make_session() -> "requests.Session":
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


# ---------------------------------------------------------------------------
# Field extraction — regex-based from program description text
# ---------------------------------------------------------------------------

def _int_from_match(m: Optional[re.Match]) -> Optional[int]:
    if m is None:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except (IndexError, ValueError):
        return None


def _float_from_match(m: Optional[re.Match]) -> Optional[float]:
    if m is None:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except (IndexError, ValueError):
        return None


def extract_fields(text: str) -> dict[str, Any]:
    """
    Parse a program description block and return structured field values.
    All fields are Optional — return None when not found, never guess.
    """
    t = text.lower()

    # ── Program type ─────────────────────────────────────────────────────
    program_type: Optional[str] = None
    type_patterns = [
        (r"\btax credit\b",          "Tax Credit"),
        (r"\bgrant\b",               "Grant"),
        (r"\bcash rebate\b",         "Cash Rebate"),
        (r"\btax exemption\b",       "Tax Exemption"),
        (r"\bsales.use tax\b",       "Sales/Use Tax Exemption"),
        (r"\bproperty tax\b",        "Property Tax Abatement"),
        (r"\bloan\b",                "Loan"),
        (r"\btraining\b.*\bgrant\b", "Job Training Grant"),
    ]
    for pattern, label in type_patterns:
        if re.search(pattern, t):
            program_type = label
            break

    # ── Jobs threshold ────────────────────────────────────────────────────
    jobs_m = re.search(
        r"(?:creat|add|hire|employ|minimum of?|at least|create)\s+(\d[\d,]*)"
        r"\s*(?:net\s+)?(?:new\s+)?(?:full[-\s]?time\s+)?(?:jobs?|employees?|positions?|workers?)\b",
        t,
    ) or re.search(
        r"\b(\d[\d,]*)\s*(?:or more\s+)?(?:net\s+)?(?:new\s+)?(?:full[-\s]?time\s+)?"
        r"(?:jobs?|employees?|positions?)\b",
        t,
    )
    jobs_threshold = _int_from_match(jobs_m)

    # ── Wage threshold ────────────────────────────────────────────────────
    # "wages at least X% of the county average" or "$N per hour" / "$N,000 per year"
    wage_m = re.search(
        r"\$\s*(\d[\d,]*)\s*(?:per\s+(?:hour|hr))",
        t,
    ) or re.search(
        r"\$\s*(\d[\d,.]+)\s*(?:k|,000)?\s*(?:per\s+(?:year|annum|employee))",
        t,
    )
    wage_threshold: Optional[float] = _float_from_match(wage_m)

    # ── Capex threshold ───────────────────────────────────────────────────
    capex_m = re.search(
        r"\$\s*(\d[\d,.]+)\s*(?:million|m)\b.*?(?:capital|invest)",
        t,
    ) or re.search(
        r"(?:capital|invest).*?\$\s*(\d[\d,.]+)\s*(?:million|m)\b",
        t,
    ) or re.search(
        r"(?:minimum|at least)\s+\$\s*(\d[\d,.]+)\s*(?:million|m)\b",
        t,
    )
    capex_raw = _float_from_match(capex_m)
    capex_threshold: Optional[float] = capex_raw * 1_000_000 if capex_raw else None

    # Fallback: "$X,000,000 in capital"
    if capex_threshold is None:
        capex_m2 = re.search(
            r"\$\s*(\d[\d,]+)\s*(?:in|of)?\s*(?:capital|investment)",
            t,
        )
        if capex_m2:
            try:
                capex_threshold = float(capex_m2.group(1).replace(",", ""))
            except ValueError:
                pass

    # ── Credit rate ───────────────────────────────────────────────────────
    rate_m = re.search(
        r"(?:credit|rebate|benefit)\s+of\s+(?:up to\s+)?(\d+(?:\.\d+)?)\s*%",
        t,
    ) or re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of|per)",
        t,
    )
    credit_rate: Optional[float] = _float_from_match(rate_m)
    if credit_rate:
        credit_rate /= 100.0          # convert 4.0 → 0.04

    # ── Award cap ─────────────────────────────────────────────────────────
    cap_m = re.search(
        r"(?:up to|maximum(?:\s+of)?|capped?\s+at)\s+\$\s*(\d[\d,.]+)"
        r"\s*(?:million|m)?\b.*?(?:per\s+(?:year|project|award|company))?",
        t,
    )
    cap_raw = _float_from_match(cap_m)
    # Determine if it's in millions (text said "million") or raw dollars
    if cap_raw and "million" in (cap_m.group(0) if cap_m else ""):
        award_cap: Optional[float] = cap_raw * 1_000_000
    elif cap_raw:
        award_cap = cap_raw
    else:
        award_cap = None

    # ── Carryforward years ────────────────────────────────────────────────
    carry_m = re.search(
        r"(\d+)\s*[-–]?\s*year\s+carry[-\s]?forward",
        t,
    ) or re.search(
        r"carry[-\s]?forward\s+(?:of\s+)?(?:up to\s+)?(\d+)\s*years?",
        t,
    )
    carryforward_years = _int_from_match(carry_m)

    # ── Refundable ────────────────────────────────────────────────────────
    refundable: Optional[bool] = None
    if re.search(r"\bnon-?refundable\b", t):
        refundable = False
    elif re.search(r"\brefundable\b", t):
        refundable = True

    # ── Sunset / status ───────────────────────────────────────────────────
    sunset_keywords = [
        "sunset", "expired", "no longer available", "discontinued",
        "repealed", "eliminated", "terminated", "closed",
    ]
    program_status = "active"
    for kw in sunset_keywords:
        if kw in t:
            program_status = "sunset"
            break

    return {
        "program_type":      program_type,
        "jobs_threshold":    jobs_threshold,
        "wage_threshold":    wage_threshold,
        "capex_threshold":   capex_threshold,
        "credit_rate":       credit_rate,
        "award_cap":         award_cap,
        "carryforward_years": carryforward_years,
        "refundable":        refundable,
        "program_status":    program_status,
    }


# ---------------------------------------------------------------------------
# HTML parsing — multiple strategies in priority order
# ---------------------------------------------------------------------------

def _parse_programs_from_html(
    html: str,
    state: str,
    source_url: str,
    log: logging.Logger,
) -> list[dict]:
    """
    Extract incentive programs from a BLS state page.

    Strategy priority:
      1. Accordion / details-summary sections (most CMS-generated sites)
      2. Heading-based sections (h2/h3 + following paragraphs)
      3. Div-based blocks with class hints
      4. Fallback: all named paragraphs

    Returns a list of raw program dicts (before field extraction).
    """
    if not HAS_BS4:
        log.error("beautifulsoup4 not installed — cannot parse HTML")
        return []

    soup = BeautifulSoup(html, "lxml" if _lxml_available() else "html.parser")

    # Remove nav, header, footer, script, style noise
    for tag in soup(["script", "style", "nav", "header", "footer", "form"]):
        tag.decompose()

    programs: list[dict] = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    # ── Strategy 1: <details>/<summary> accordion ──────────────────────────
    for details in soup.find_all("details"):
        summary = details.find("summary")
        if summary:
            name = summary.get_text(separator=" ").strip()
            body = details.get_text(separator=" ").strip()
            body = body.replace(name, "", 1).strip()
            if len(name) > 4:
                fields = extract_fields(body)
                programs.append({
                    "state": state,
                    "program_name": name,
                    "description": body[:1000],
                    "source_url": source_url,
                    "scraped_at": scraped_at,
                    "extraction_method": "accordion-details",
                    **fields,
                })

    if programs:
        log.debug(f"  [{state}] strategy=accordion-details found {len(programs)} programs")
        return programs

    # ── Strategy 2: Heading-based sections ────────────────────────────────
    # Look for h2/h3 headings that look like program names (not navigation)
    NAV_WORDS = {"contact", "home", "about", "services", "blog", "news",
                 "states", "programs", "locations", "overview", "resources"}

    for heading_tag in ["h2", "h3", "h4"]:
        for h in soup.find_all(heading_tag):
            name = h.get_text(separator=" ").strip()
            if not name or len(name) < 6 or name.lower() in NAV_WORDS:
                continue
            # Skip if name looks like it's just a state heading
            if name.strip().lower() in [s.lower() for s in STATE_SLUGS]:
                continue

            # Collect following sibling text until next same-level heading
            body_parts: list[str] = []
            for sibling in h.next_siblings:
                if sibling.name in [heading_tag, "h1", "h2", "h3", "h4"]:
                    break
                if hasattr(sibling, "get_text"):
                    t = sibling.get_text(separator=" ").strip()
                    if t:
                        body_parts.append(t)
            body = " ".join(body_parts).strip()

            if len(body) > 30:  # must have some substance
                fields = extract_fields(body)
                programs.append({
                    "state": state,
                    "program_name": name,
                    "description": body[:1000],
                    "source_url": source_url,
                    "scraped_at": scraped_at,
                    "extraction_method": f"heading-{heading_tag}",
                    **fields,
                })

        if programs:
            log.debug(f"  [{state}] strategy=heading-{heading_tag} found {len(programs)} programs")
            return programs

    # ── Strategy 3: Div blocks with class hints ───────────────────────────
    CLASS_HINTS = re.compile(r"program|incentive|accordion|toggle|item|card|entry", re.I)
    for div in soup.find_all("div", class_=CLASS_HINTS):
        # Find a "title" child
        title_el = div.find(["h2", "h3", "h4", "strong", "b", "span"], class_=re.compile(r"title|name|header", re.I))
        if title_el is None:
            title_el = div.find(["h2", "h3", "h4"])
        if title_el is None:
            continue
        name = title_el.get_text(separator=" ").strip()
        if not name or len(name) < 6:
            continue
        body = div.get_text(separator=" ").strip().replace(name, "", 1).strip()
        if len(body) > 30:
            fields = extract_fields(body)
            programs.append({
                "state": state,
                "program_name": name,
                "description": body[:1000],
                "source_url": source_url,
                "scraped_at": scraped_at,
                "extraction_method": "div-class",
                **fields,
            })

    if programs:
        log.debug(f"  [{state}] strategy=div-class found {len(programs)} programs")
        return programs

    # ── Strategy 4: Fallback — log what we see ────────────────────────────
    all_text = soup.get_text(separator="\n").strip()
    log.warning(
        f"[{state}] All parsing strategies failed. Page text preview:\n"
        f"{all_text[:500]}"
    )
    return []


def _lxml_available() -> bool:
    try:
        import lxml  # noqa
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Mock data — used when --mock is passed or network is unavailable
# ---------------------------------------------------------------------------

def _build_mock_data(states: list[str], log: logging.Logger) -> list[dict]:
    """
    Returns realistic mock program records for testing the pipeline
    without network access. Includes examples of all three change scenarios.
    """
    scraped_at = datetime.now(timezone.utc).isoformat()

    mock: list[dict] = [

        # ── ALABAMA ──────────────────────────────────────────────────────
        {
            "state": "Alabama",
            "program_name": "Jobs Act Incentives: Jobs",
            "program_type": "Cash Rebate",
            "jobs_threshold": 50,
            "wage_threshold": None,
            "capex_threshold": 2_000_000,
            "credit_rate": 0.04,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "The Jobs Act provides cash rebates of up to 4% of prior-year gross "
                "payroll for qualifying jobs. Companies must create at least 50 net new "
                "full-time jobs in non-targeted counties (10 in targeted/Jumpstart counties) "
                "and invest at least $2 million in capital."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/alabama",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Alabama",
            "program_name": "Jobs Act Incentives: Investment",
            "program_type": "Tax Abatement",
            "jobs_threshold": 50,
            "wage_threshold": None,
            "capex_threshold": 2_000_000,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": None,
            "program_status": "active",
            "description": (
                "The Jobs Act investment component provides abatements on state and non-educational "
                "county property taxes and sales/use taxes on construction materials, equipment, "
                "and machinery for qualifying projects with at least 50 jobs and $2 million in capital."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/alabama",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Alabama",
            "program_name": "Sales Tax Exemptions",
            "program_type": "Sales/Use Tax Exemption",
            "jobs_threshold": None,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": None,
            "program_status": "active",
            "description": (
                "Alabama provides exemptions from the 4% state sales and use tax on purchases of "
                "manufacturing machinery and equipment, raw materials, and fuels used in manufacturing."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/alabama",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Alabama",
            # NOTE: Parameter change scenario — jobs threshold updated on BLS vs model
            "program_name": "Property Tax Abatements",
            "program_type": "Property Tax Abatement",
            "jobs_threshold": 50,         # ← changed (model had no explicit threshold documented)
            "wage_threshold": None,
            "capex_threshold": 2_000_000,  # ← BLS now explicitly states this
            "credit_rate": 1.0,            # 100% abatement
            "award_cap": None,
            "carryforward_years": None,
            "refundable": None,
            "program_status": "active",
            "description": (
                "Qualified projects may receive abatements on property taxes for up to 20 years "
                "(30 years for large projects) for non-educational property taxes on real and "
                "personal property. Minimum 50 jobs and $2 million capital investment required."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/alabama",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        # NOTE: "Enterprise Zone credit/exemption" intentionally omitted from mock BLS data
        #       → will surface as "unverified" (Scenario 1)
        {
            # NEW CANDIDATE — not in our model (Scenario 2)
            "state": "Alabama",
            "program_name": "Alabama Innovation Fund",
            "program_type": "Grant",
            "jobs_threshold": 10,
            "wage_threshold": None,
            "capex_threshold": 500_000,
            "credit_rate": None,
            "award_cap": 1_000_000,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "The Alabama Innovation Fund provides competitive grants of up to $1 million "
                "to companies commercializing innovative technologies in Alabama. Applicants "
                "must create at least 10 jobs and invest at least $500,000."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/alabama",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },

        # ── VIRGINIA ─────────────────────────────────────────────────────
        {
            "state": "Virginia",
            "program_name": "Enterprise Zone Job Creation Grant",
            "program_type": "Grant",
            "jobs_threshold": 4,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": None,
            "award_cap": 800,           # $800 per job (not a cap in the traditional sense)
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "Eligible businesses in Enterprise Zones may receive annual grants of $500 to $800 "
                "per net new job (at least 4 new jobs required) for up to 5 years. Wages must "
                "meet or exceed the lower of the federal or state minimum wage."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Enterprise Zone Real Property Investment Grant",
            "program_type": "Grant",
            "jobs_threshold": None,
            "wage_threshold": None,
            "capex_threshold": 100_000,
            "credit_rate": None,
            "award_cap": 100_000,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "Businesses making qualifying real property investments in Enterprise Zones may "
                "receive grants of 20% of qualified real property investment up to a maximum of "
                "$100,000 per building. Minimum investment of $100,000 required."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Sales Tax Exemptions for Manufacturing",
            "program_type": "Sales/Use Tax Exemption",
            "jobs_threshold": None,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": None,
            "program_status": "active",
            "description": (
                "Virginia provides a sales and use tax exemption on machinery and equipment used "
                "directly in manufacturing, processing, mining, and refining. Qualifying equipment "
                "must be used directly in production."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Data Center Sales Tax Exemption",
            "program_type": "Sales/Use Tax Exemption",
            "jobs_threshold": 50,
            "wage_threshold": 150_000,
            "capex_threshold": 150_000_000,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": None,
            "program_status": "active",
            "description": (
                "Qualifying data centers may receive full exemption from sales and use taxes "
                "on computer equipment, software, and enabling hardware. Minimum 50 jobs paying "
                "an average of $150,000 or more and $150 million in capital investment required."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Major Research and Development Expenses Tax Credit",
            "program_type": "Tax Credit",
            "jobs_threshold": None,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": 0.15,
            "award_cap": None,
            "carryforward_years": 10,
            "refundable": False,
            "program_status": "active",
            "description": (
                "Virginia provides a non-refundable income tax credit equal to 15% of qualifying "
                "R&D expenditures that exceed the Virginia base amount. Excess credits may be "
                "carried forward for up to 10 years."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Refundable R&D Expense Tax Credit",
            "program_type": "Tax Credit",
            "jobs_threshold": None,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": 0.15,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "Virginia offers a refundable income tax credit of 15% of qualifying R&D expenses "
                "for companies with Virginia R&D expenses of $5 million or less."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            # PARAMETER CHANGE scenario — credit per job updated on BLS
            "program_name": "Major Business Facility Job Tax Credit",
            "program_type": "Tax Credit",
            "jobs_threshold": 100,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": 5,
            "refundable": False,
            "program_status": "active",
            "description": (
                "Provides a $1,000 credit per net new permanent full-time job for companies that "
                "create 100 or more jobs. Credits may be carried forward for up to 5 years. "
                "Note: The minimum job threshold was recently increased from 50 to 100 jobs."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Virginia Jobs Investment Program (VJIP)",
            "program_type": "Job Training Grant",
            "jobs_threshold": 25,
            "wage_threshold": None,
            "capex_threshold": None,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "VJIP provides customized recruitment and training services to companies creating "
                "at least 25 new jobs. Assistance ranges from $100 to $500 per new employee "
                "depending on project type and wage level."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            "state": "Virginia",
            "program_name": "Virginia Talent Accelerator Program",
            "program_type": "Job Training Grant",
            "jobs_threshold": 25,
            "wage_threshold": 50_000,
            "capex_threshold": None,
            "credit_rate": None,
            "award_cap": None,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "Provides fully customized workforce recruitment and training services at no cost "
                "to qualifying companies. Requires at least 25 new jobs paying above $50,000 annually."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
        {
            # NEW CANDIDATE — found on BLS but not in our model (Scenario 2)
            "state": "Virginia",
            "program_name": "GO Virginia Regional Competitiveness Grant",
            "program_type": "Grant",
            "jobs_threshold": 35,
            "wage_threshold": 55_000,
            "capex_threshold": 2_000_000,
            "credit_rate": None,
            "award_cap": 3_000_000,
            "carryforward_years": None,
            "refundable": True,
            "program_status": "active",
            "description": (
                "GO Virginia grants support regional economic development projects that create "
                "at least 35 new jobs at or above the regional median wage. Awards up to "
                "$3 million per project are available from the Growth and Opportunity for Virginia fund."
            ),
            "source_url": "https://www.blsstrategies.com/incentives/virginia",
            "scraped_at": scraped_at,
            "extraction_method": "mock",
        },
    ]

    # Filter to requested states only
    requested = {s.lower() for s in states}
    if requested != {"all"}:
        mock = [r for r in mock if r["state"].lower() in requested]

    log.info(f"[MOCK] Generated {len(mock)} program records for states: {states}")
    return mock


# ---------------------------------------------------------------------------
# Scraper core
# ---------------------------------------------------------------------------

class BLSScraper:

    FIELDS = [
        "state", "program_name", "program_type",
        "jobs_threshold", "wage_threshold", "capex_threshold",
        "credit_rate", "award_cap", "carryforward_years",
        "refundable", "program_status",
        "description", "source_url", "scraped_at", "extraction_method",
    ]

    def __init__(self, delay: float = REQUEST_DELAY, verbose: bool = False):
        self.delay = delay
        self.log   = _setup_logging(verbose)
        self._session: Optional["requests.Session"] = None
        self.failed_pages: list[dict] = []
        self.all_programs: list[dict] = []

    @property
    def session(self) -> "requests.Session":
        if self._session is None:
            self._session = _make_session()
        return self._session

    def scrape_state(self, state: str) -> list[dict]:
        """Fetch and parse one state page. Returns list of program dicts."""
        if not HAS_REQUESTS:
            self.log.error("'requests' package not installed. Run: pip install requests beautifulsoup4 lxml")
            return []
        if not HAS_BS4:
            self.log.error("'beautifulsoup4' not installed. Run: pip install beautifulsoup4 lxml")
            return []

        slug = STATE_SLUGS.get(state)
        if not slug:
            self.log.warning(f"[{state}] No URL slug — skipping")
            return []

        url = f"{BASE_URL}/{slug}"
        self.log.info(f"[{state}] GET {url}")

        try:
            resp = self.session.get(url, timeout=20)
        except Exception as exc:
            self.log.error(f"[{state}] Request failed: {type(exc).__name__}: {exc}")
            self.failed_pages.append({"state": state, "url": url, "error": str(exc)})
            return []

        if resp.status_code == 404:
            self.log.warning(f"[{state}] 404 — page not found. State may not have a BLS page yet.")
            self.failed_pages.append({"state": state, "url": url, "error": "404 Not Found"})
            return []

        if resp.status_code != 200:
            self.log.error(f"[{state}] HTTP {resp.status_code}")
            self.failed_pages.append({"state": state, "url": url, "error": f"HTTP {resp.status_code}"})
            return []

        programs = _parse_programs_from_html(resp.text, state, url, self.log)
        self.log.info(f"[{state}] Extracted {len(programs)} programs")
        return programs

    def scrape_states(self, states: list[str]) -> list[dict]:
        """Scrape multiple states with polite delay between requests."""
        all_programs: list[dict] = []
        for i, state in enumerate(states):
            if i > 0:
                time.sleep(self.delay)
            programs = self.scrape_state(state)
            all_programs.extend(programs)

        self.all_programs = all_programs
        return all_programs

    def save(self, programs: list[dict], output_path: Optional[Path] = None) -> Path:
        out = output_path or (_DATA / "bls_current.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(programs, f, indent=2, ensure_ascii=False)
        self.log.info(f"Saved {len(programs)} programs → {out}")
        return out

    def print_summary(self, programs: list[dict]) -> None:
        from collections import Counter
        states = Counter(p["state"] for p in programs)
        methods = Counter(p.get("extraction_method", "?") for p in programs)
        null_counts: dict[str, int] = {}
        for field in ["jobs_threshold", "wage_threshold", "capex_threshold",
                      "credit_rate", "award_cap", "carryforward_years", "refundable"]:
            null_counts[field] = sum(1 for p in programs if p.get(field) is None)

        self.log.info("─" * 60)
        self.log.info(f"SCRAPE SUMMARY — {len(programs)} programs across {len(states)} states")
        self.log.info(f"Extraction methods: {dict(methods)}")
        self.log.info("Null field rates (lower is better):")
        for field, n in null_counts.items():
            pct = n / len(programs) * 100 if programs else 0
            self.log.info(f"  {field:<22} {n:>3} null  ({pct:.0f}%)")
        if self.failed_pages:
            self.log.warning(f"Failed pages ({len(self.failed_pages)}):")
            for fp in self.failed_pages:
                self.log.warning(f"  {fp['state']}: {fp['error']}")
        self.log.info("─" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _load_state_list() -> list[str]:
    """Read all unique state names from incentive_programs.txt."""
    if not _PROGRAMS_TXT.exists():
        return list(STATE_SLUGS.keys())
    states = set()
    for line in _PROGRAMS_TXT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "_" in line:
            state = line.split("_", 1)[0]
            if state:
                states.add(state)
    return sorted(states)


def main() -> None:
    parser = argparse.ArgumentParser(description="BLS Strategies Incentive Scraper")
    parser.add_argument(
        "--states", nargs="+", metavar="STATE",
        help="Specific states to scrape (default: all states in program database)"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use built-in mock data instead of live scraping (for testing)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scrape but do not write output file"
    )
    parser.add_argument(
        "--output", metavar="PATH",
        help=f"Output JSON path (default: data/bls_current.json)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Debug logging"
    )
    parser.add_argument(
        "--delay", type=float, default=REQUEST_DELAY, metavar="SECONDS",
        help=f"Seconds between requests (default: {REQUEST_DELAY})"
    )
    args = parser.parse_args()

    # Resolve state list
    if args.states:
        # Normalise user input to title case
        requested_states = [s.title() for s in args.states]
        # Validate
        unknown = [s for s in requested_states if s not in STATE_SLUGS]
        if unknown:
            print(f"Unknown states: {unknown}")
            print(f"Valid states: {list(STATE_SLUGS.keys())}")
            sys.exit(1)
        states = requested_states
    else:
        states = _load_state_list()

    scraper = BLSScraper(delay=args.delay, verbose=args.verbose)

    if args.mock:
        scraper.log.info("Running in MOCK mode — no network requests")
        programs = _build_mock_data(states, scraper.log)
    else:
        if not HAS_REQUESTS or not HAS_BS4:
            scraper.log.error(
                "Missing dependencies. Install with:\n"
                "  pip install requests beautifulsoup4 lxml\n"
                "Or use --mock to test without live scraping."
            )
            sys.exit(1)
        programs = scraper.scrape_states(states)

    scraper.print_summary(programs)

    if not args.dry_run:
        out_path = Path(args.output) if args.output else None
        saved = scraper.save(programs, out_path)
        print(f"\n✓ Output saved to: {saved}")
    else:
        print(f"\n[dry-run] Would save {len(programs)} programs — no file written")


if __name__ == "__main__":
    main()
