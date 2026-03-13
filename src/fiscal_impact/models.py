"""
models.py — Data models for the Fiscal Impact Engine.

Four core dataclasses:
    ProjectInputs      — all user-supplied project parameters
    LocationRates      — all tax rates for a given state/county/city
    FiscalTimeSeries   — year-by-year revenue and employment arrays
    FiscalSummary      — scalar NPV / breakeven / headline results
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# ProjectInputs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProjectInputs:
    """
    All user-supplied parameters that describe an economic development project.

    Required fields are annotated; optional fields have defaults.
    Validation is performed in __post_init__.
    """

    # ── Location ──────────────────────────────────────────────────────────────
    state:    str                          # e.g., "Virginia"
    county:   Optional[str] = None         # e.g., "Henrico County"
    city:     Optional[str] = None         # e.g., "Richmond"

    # ── Employment ────────────────────────────────────────────────────────────
    direct_jobs:      int   = 0            # total promised direct positions
    average_salary:   float = 65_000.0     # average annual salary for direct workers ($)
    ramp_up_years:    int   = 3            # years to reach full employment
    project_start_year: int = 2025         # calendar year of project Year 1

    # ── Capital Investment ────────────────────────────────────────────────────
    capital_investment:  float = 0.0       # total promised capex ($)
    project_type:        str   = "commercial"  # 'commercial' | 'industrial' | 'data_center'
    construction_years:  int   = 2         # years over which capex is deployed

    # ── Analysis Horizon ──────────────────────────────────────────────────────
    analysis_years:   int   = 10           # total projection years
    discount_type:    str   = "societal"   # 'societal' (3%) | 'corporate' (12%)

    # ── Project Sector (for RIMS II and IRS lookups) ─────────────────────────
    rims2_sector:   Optional[str] = None   # RIMS II sector name (None → default for state)
    irs_sector:     Optional[str] = None   # IRS NAICS sector name (None → national avg)

    # ── Hardcoded constants from session brief ────────────────────────────────
    # These can be overridden but default to the brief-specified values
    taxable_spend_share:          float = 0.3765   # 37.65% of income is taxable spending
    federal_payroll_tax_rate:     float = 0.059    # SS + Medicare + FUTA (5.9%)
    residents_in_same_locality:   float = 0.23     # 23% of workers live in project locality
    building_sq_ft_per_worker:    float = 300.0    # sq ft per employee

    # ── Depreciation schedule (real property assessed value decay) ────────────
    # Year index → depreciation fraction; defaults per session brief
    depreciation_schedule: Optional[Dict[int, float]] = None
    # Default: Year 1–3 = 100%, Year 4 = 90%, Year 5 = 80%

    def __post_init__(self):
        # Validate state
        if not self.state or not isinstance(self.state, str):
            raise ValueError("state must be a non-empty string")

        # Coerce types
        self.direct_jobs       = int(self.direct_jobs)
        self.average_salary    = float(self.average_salary)
        self.capital_investment = float(self.capital_investment)
        self.analysis_years    = int(self.analysis_years)

        if self.direct_jobs < 0:
            raise ValueError(f"direct_jobs must be >= 0, got {self.direct_jobs}")
        if self.average_salary <= 0:
            raise ValueError(f"average_salary must be > 0, got {self.average_salary}")
        if self.analysis_years < 1:
            raise ValueError(f"analysis_years must be >= 1, got {self.analysis_years}")
        if self.ramp_up_years < 0 or self.ramp_up_years > self.analysis_years:
            raise ValueError(f"ramp_up_years {self.ramp_up_years} must be in [0, {self.analysis_years}]")

        # Default depreciation schedule
        if self.depreciation_schedule is None:
            self.depreciation_schedule = {
                1: 1.00, 2: 1.00, 3: 1.00,
                4: 0.90, 5: 0.80,
            }

        # Normalize project_type
        self.project_type = self.project_type.lower()

        # Normalize discount_type
        self.discount_type = self.discount_type.lower()
        if self.discount_type not in ("societal", "corporate"):
            raise ValueError(f"discount_type must be 'societal' or 'corporate', got '{self.discount_type}'")

    def get_depreciation_factor(self, year: int) -> float:
        """
        Assessed value as fraction of original capex for a given project year.
        After the defined schedule, remains at 80% (fully depreciated floor).
        """
        return self.depreciation_schedule.get(year, 0.80)

    def get_employment_ramp(self) -> List[float]:
        """
        Return list of direct employment fractions for each project year
        [year_1_fraction, year_2_fraction, ..., year_n_fraction].

        Linear ramp from 0 to 1.0 over ramp_up_years, then full employment.
        """
        fracs = []
        for yr in range(1, self.analysis_years + 1):
            if self.ramp_up_years <= 0:
                frac = 1.0
            elif yr <= self.ramp_up_years:
                frac = yr / self.ramp_up_years
            else:
                frac = 1.0
            fracs.append(frac)
        return fracs

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectInputs":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────────────
# LocationRates
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LocationRates:
    """
    All tax rates and economic parameters for a given state/county/city.

    Typically populated by RatesDB.get_location_rates(), but can be
    constructed manually for custom scenarios.
    """

    # ── Location identifier ───────────────────────────────────────────────────
    state:  str
    county: Optional[str] = None
    city:   Optional[str] = None

    # ── Income tax ────────────────────────────────────────────────────────────
    pit_effective_rate: float = 0.0   # effective PIT rate at project's avg salary
    pit_marginal_rate:  float = 0.0   # marginal PIT rate

    # ── Sales tax ─────────────────────────────────────────────────────────────
    sales_tax_rate:       float = 0.0  # combined state + local
    sales_tax_state_only: float = 0.0
    sales_tax_local_only: float = 0.0

    # ── Business taxes ────────────────────────────────────────────────────────
    cit_rate:              float = 0.0  # state corporate income tax rate
    grt_rate:              float = 0.0  # gross receipts tax rate (0 if none)
    bpol_rate_professional: float = 0.0 # Business/Occupational License (Richmond VA only)
    bpol_rate_retail:       float = 0.0

    # ── Property tax ──────────────────────────────────────────────────────────
    property_tax_rate: float = 0.012   # effective commercial property tax rate

    # ── RIMS II multipliers ────────────────────────────────────────────────────
    rims2: Dict = field(default_factory=lambda: {
        "output_mult": 1.5,
        "earnings_mult": 0.6,
        "employment_mult": 12.0,
        "value_added_mult": 0.9,
        "direct_earnings_mult": 1.0,
        "direct_employment_mult": 1.0,
        "sector": "default",
    })

    # ── Wages ─────────────────────────────────────────────────────────────────
    state_avg_annual_wage: float = 57_000.0   # BLS QCEW average for indirect/induced

    # ── IRS payroll-to-receipts ───────────────────────────────────────────────
    payroll_to_receipts_ratio:  float = 0.1052   # national average
    receipts_to_payroll_mult:   float = 9.51     # = 1 / payroll_to_receipts_ratio

    # ── Economic rates ────────────────────────────────────────────────────────
    eci_inflation:           float = 0.032
    cpi_inflation:           float = 0.0273
    ppi_inflation:           float = 0.0232
    cre_inflation:           float = 0.0440
    societal_discount_rate:  float = 0.03
    corporate_discount_rate: float = 0.12

    # ── Utility assumptions ───────────────────────────────────────────────────
    building_sqft_per_worker: float = 300.0
    electricity_kwh_per_sqft: float = 13.63
    gas_cuft_per_sqft:        float = 14.57

    # ── Consumer spending ─────────────────────────────────────────────────────
    taxable_spend_share: float = 0.3765

    # ── Capex splits ──────────────────────────────────────────────────────────
    capex_splits: Dict[str, float] = field(default_factory=dict)

    def get_discount_rate(self, discount_type: str = "societal") -> float:
        if discount_type == "corporate":
            return self.corporate_discount_rate
        return self.societal_discount_rate

    @classmethod
    def from_rates_db(cls, db, inputs: ProjectInputs) -> "LocationRates":
        """
        Populate from a RatesDB instance using the given ProjectInputs.
        """
        raw = db.get_location_rates(
            state=inputs.state,
            county=inputs.county,
            city=inputs.city,
            project_type=inputs.project_type,
            rims2_sector=inputs.rims2_sector,
            irs_sector=inputs.irs_sector,
            average_salary=inputs.average_salary,
        )
        return cls(
            state=inputs.state,
            county=inputs.county,
            city=inputs.city,
            **{k: v for k, v in raw.items() if k in cls.__dataclass_fields__},
        )

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# FiscalTimeSeries
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FiscalTimeSeries:
    """
    Year-by-year fiscal and employment arrays for the analysis period.

    All arrays are indexed starting at year 1 (array[0] = Year 1).
    Revenue arrays represent annual LOCAL government revenues in nominal dollars.
    """

    years: int                              # number of projection years
    calendar_years: List[int] = field(default_factory=list)

    # ── Employment ────────────────────────────────────────────────────────────
    direct_jobs:   List[float] = field(default_factory=list)   # FTE by year
    indirect_jobs: List[float] = field(default_factory=list)   # via RIMS II
    induced_jobs:  List[float] = field(default_factory=list)   # via RIMS II
    total_jobs:    List[float] = field(default_factory=list)

    # ── Payroll & gross receipts ───────────────────────────────────────────────
    direct_payroll:    List[float] = field(default_factory=list)
    gross_receipts:    List[float] = field(default_factory=list)  # from IRS ratio

    # ── Revenue streams (local government) ────────────────────────────────────
    revenue_pit:         List[float] = field(default_factory=list)  # personal income tax
    revenue_sales_tax:   List[float] = field(default_factory=list)  # consumer sales tax
    revenue_bpol:        List[float] = field(default_factory=list)  # BPOL (RVA only)
    revenue_cit:         List[float] = field(default_factory=list)  # corporate income tax
    revenue_grt:         List[float] = field(default_factory=list)  # gross receipts tax
    revenue_property:    List[float] = field(default_factory=list)  # real + personal prop
    revenue_utility:     List[float] = field(default_factory=list)  # utility taxes

    # ── Totals ─────────────────────────────────────────────────────────────────
    total_local_revenue: List[float] = field(default_factory=list)  # sum of all above
    cumulative_revenue:  List[float] = field(default_factory=list)  # running cumulative

    def validate(self):
        """Assert all arrays have length == self.years."""
        arrays = [
            "direct_jobs", "indirect_jobs", "induced_jobs", "total_jobs",
            "direct_payroll", "gross_receipts",
            "revenue_pit", "revenue_sales_tax", "revenue_bpol",
            "revenue_cit", "revenue_grt", "revenue_property", "revenue_utility",
            "total_local_revenue", "cumulative_revenue",
        ]
        for name in arrays:
            arr = getattr(self, name)
            if arr and len(arr) != self.years:
                raise ValueError(
                    f"FiscalTimeSeries.{name} has {len(arr)} elements, expected {self.years}"
                )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_table(self) -> List[dict]:
        """Convert to a list of per-year dicts (convenient for DataFrame construction)."""
        cal = self.calendar_years or list(range(1, self.years + 1))
        rows = []
        for i in range(self.years):
            rows.append({
                "year":           i + 1,
                "calendar_year":  cal[i] if i < len(cal) else None,
                "direct_jobs":    self.direct_jobs[i]    if self.direct_jobs    else 0,
                "indirect_jobs":  self.indirect_jobs[i]  if self.indirect_jobs  else 0,
                "induced_jobs":   self.induced_jobs[i]   if self.induced_jobs   else 0,
                "total_jobs":     self.total_jobs[i]     if self.total_jobs     else 0,
                "direct_payroll": self.direct_payroll[i] if self.direct_payroll else 0,
                "gross_receipts": self.gross_receipts[i] if self.gross_receipts else 0,
                "rev_pit":        self.revenue_pit[i]       if self.revenue_pit       else 0,
                "rev_sales":      self.revenue_sales_tax[i] if self.revenue_sales_tax else 0,
                "rev_bpol":       self.revenue_bpol[i]      if self.revenue_bpol      else 0,
                "rev_cit":        self.revenue_cit[i]       if self.revenue_cit       else 0,
                "rev_grt":        self.revenue_grt[i]       if self.revenue_grt       else 0,
                "rev_property":   self.revenue_property[i]  if self.revenue_property  else 0,
                "rev_utility":    self.revenue_utility[i]   if self.revenue_utility   else 0,
                "total_revenue":  self.total_local_revenue[i] if self.total_local_revenue else 0,
                "cumulative":     self.cumulative_revenue[i]  if self.cumulative_revenue  else 0,
            })
        return rows

    def print_table(self, calendar_start: Optional[int] = None):
        """Print a formatted year-by-year table."""
        cal = self.calendar_years or list(range(1, self.years + 1))
        header = (
            f"{'Yr':>3}  {'Cal':>5}  {'Dir Jobs':>9}  {'Tot Jobs':>9}  "
            f"{'Payroll':>12}  {'PIT':>10}  {'Sales':>10}  "
            f"{'Prop':>10}  {'BPOL':>8}  {'Total Rev':>12}  {'Cumulative':>13}"
        )
        print(header)
        print("-" * len(header))
        for row in self.to_table():
            print(
                f"{row['year']:>3}  {row['calendar_year']:>5}  "
                f"{row['direct_jobs']:>9,.1f}  {row['total_jobs']:>9,.1f}  "
                f"{row['direct_payroll']:>12,.0f}  "
                f"{row['rev_pit']:>10,.0f}  {row['rev_sales']:>10,.0f}  "
                f"{row['rev_property']:>10,.0f}  {row['rev_bpol']:>8,.0f}  "
                f"{row['total_revenue']:>12,.0f}  {row['cumulative']:>13,.0f}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# FiscalSummary
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FiscalSummary:
    """
    Scalar summary of fiscal impact results.

    Headline outputs used for reporting and Richmond benchmark validation.
    """

    # ── Inputs echo ────────────────────────────────────────────────────────────
    state:              str   = ""
    city:               Optional[str] = None
    direct_jobs:        int   = 0
    average_salary:     float = 0.0
    capital_investment: float = 0.0
    project_start_year: int   = 2025
    analysis_years:     int   = 10

    # ── Employment outcomes ────────────────────────────────────────────────────
    total_direct_jobs_y1:    float = 0.0   # Year 1 direct FTE
    total_jobs_at_maturity:  float = 0.0   # total jobs (direct + indirect + induced) at full ramp
    employment_multiplier:   float = 0.0   # from RIMS II

    # ── Revenue — Year 1 ──────────────────────────────────────────────────────
    y1_revenue_pit:       float = 0.0
    y1_revenue_sales:     float = 0.0
    y1_revenue_bpol:      float = 0.0
    y1_revenue_cit:       float = 0.0
    y1_revenue_grt:       float = 0.0
    y1_revenue_property:  float = 0.0
    y1_revenue_utility:   float = 0.0
    y1_total_revenue:     float = 0.0

    # ── NPV / present value ────────────────────────────────────────────────────
    npv_total_revenue:    float = 0.0   # PV of all local revenues over analysis period
    npv_incentive_cost:   float = 0.0   # PV of any incentives / foregone revenue (if modelled)
    discount_rate_used:   float = 0.03

    # ── Breakeven analysis ─────────────────────────────────────────────────────
    cumulative_revenue_by_year: Dict[int, float] = field(default_factory=dict)
    breakeven_year:        Optional[int] = None    # project year of payback
    breakeven_calendar_year: Optional[int] = None  # calendar year
    total_10yr_revenue:    float = 0.0

    # ── Rates used ────────────────────────────────────────────────────────────
    pit_effective_rate:  float = 0.0
    sales_tax_rate:      float = 0.0
    property_tax_rate:   float = 0.0
    cit_rate:            float = 0.0
    grt_rate:            float = 0.0
    bpol_rate:           float = 0.0

    def print_headline(self):
        """Print a human-readable summary card."""
        print("=" * 60)
        print(f"  FISCAL IMPACT SUMMARY")
        print(f"  {self.state}{' / ' + self.city if self.city else ''}")
        print("=" * 60)
        print(f"  Direct jobs:         {self.direct_jobs:,}")
        print(f"  Avg salary:          ${self.average_salary:,.0f}")
        print(f"  Capital investment:  ${self.capital_investment:,.0f}")
        print(f"  Project start:       {self.project_start_year}")
        print()
        print(f"  ── Year 1 Revenue Breakdown ──")
        print(f"  Personal income tax: ${self.y1_revenue_pit:,.0f}")
        print(f"  Sales tax:           ${self.y1_revenue_sales:,.0f}")
        if self.y1_revenue_bpol > 0:
            print(f"  BPOL:                ${self.y1_revenue_bpol:,.0f}")
        if self.y1_revenue_cit > 0:
            print(f"  Corporate inc. tax:  ${self.y1_revenue_cit:,.0f}")
        if self.y1_revenue_grt > 0:
            print(f"  Gross receipts tax:  ${self.y1_revenue_grt:,.0f}")
        print(f"  Property tax:        ${self.y1_revenue_property:,.0f}")
        if self.y1_revenue_utility > 0:
            print(f"  Utility taxes:       ${self.y1_revenue_utility:,.0f}")
        print(f"  ─────────────────────────────")
        print(f"  TOTAL Year 1:        ${self.y1_total_revenue:,.0f}")
        print()
        print(f"  NPV ({self.discount_rate_used*100:.0f}% rate):      ${self.npv_total_revenue:,.0f}")
        print(f"  10-yr total revenue: ${self.total_10yr_revenue:,.0f}")
        if self.breakeven_calendar_year:
            print(f"  Breakeven year:      {self.breakeven_calendar_year} (project yr {self.breakeven_year})")
        else:
            print(f"  Breakeven year:      N/A within {self.analysis_years}-yr window")
        print("=" * 60)

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    errors = []

    def check(label, got, expected, tol=0.01):
        ok = got == expected if isinstance(expected, (str, type(None))) else abs(got - expected) / (abs(expected) + 1e-9) < tol
        print(f"  {'✅' if ok else '❌'} {label}: {got}")
        if not ok:
            errors.append(f"{label}: got {got}, expected {expected}")

    print("── ProjectInputs ────────────────────────────────────────────────────")

    # Richmond validation project
    proj = ProjectInputs(
        state="Virginia",
        city="Richmond",
        direct_jobs=250,
        average_salary=75_000,
        capital_investment=5_000_000,
        ramp_up_years=3,
        project_start_year=2025,
        analysis_years=10,
        project_type="commercial",
        discount_type="societal",
    )
    ramp = proj.get_employment_ramp()
    check("ramp year 1 = 1/3",      ramp[0], 1/3,  tol=0.01)
    check("ramp year 3 = 1.0",      ramp[2], 1.0,  tol=0.001)
    check("ramp year 4 = 1.0",      ramp[3], 1.0,  tol=0.001)
    check("depreciation y1 = 1.0",  proj.get_depreciation_factor(1), 1.0, tol=0.001)
    check("depreciation y4 = 0.9",  proj.get_depreciation_factor(4), 0.9, tol=0.001)
    check("depreciation y6 = 0.8",  proj.get_depreciation_factor(6), 0.8, tol=0.001)

    print("\n── LocationRates default ────────────────────────────────────────────")
    lr = LocationRates(state="Virginia", city="Richmond")
    check("property tax default", lr.property_tax_rate, 0.012, tol=0.1)
    check("discount rate (societal)", lr.get_discount_rate("societal"), 0.03, tol=0.001)
    check("discount rate (corporate)", lr.get_discount_rate("corporate"), 0.12, tol=0.001)

    print("\n── FiscalTimeSeries ─────────────────────────────────────────────────")
    ts = FiscalTimeSeries(
        years=5,
        calendar_years=[2025, 2026, 2027, 2028, 2029],
        direct_jobs=[83.3, 166.7, 250.0, 250.0, 250.0],
        total_jobs=[100.0, 200.0, 300.0, 300.0, 300.0],
        indirect_jobs=[10.0, 20.0, 30.0, 30.0, 30.0],
        induced_jobs=[6.7, 13.3, 20.0, 20.0, 20.0],
        direct_payroll=[6_250_000, 12_500_000, 18_750_000, 19_350_000, 19_969_200],
        gross_receipts=[0]*5,
        revenue_pit=[100_000]*5,
        revenue_sales_tax=[50_000]*5,
        revenue_bpol=[5_000]*5,
        revenue_cit=[10_000]*5,
        revenue_grt=[0]*5,
        revenue_property=[30_000]*5,
        revenue_utility=[2_000]*5,
        total_local_revenue=[197_000]*5,
        cumulative_revenue=[197_000, 394_000, 591_000, 788_000, 985_000],
    )
    ts.validate()
    table = ts.to_table()
    check("table len", len(table), 5)
    check("table y1 total", table[0]["total_revenue"], 197_000, tol=0.001)
    print()
    ts.print_table()

    print("\n── FiscalSummary ────────────────────────────────────────────────────")
    fs = FiscalSummary(
        state="Virginia",
        city="Richmond",
        direct_jobs=250,
        average_salary=75_000,
        capital_investment=5_000_000,
        project_start_year=2025,
        y1_total_revenue=42_714,
        npv_total_revenue=350_000,
        total_10yr_revenue=500_000,
        breakeven_year=8,
        breakeven_calendar_year=2032,
    )
    fs.print_headline()

    print()
    if errors:
        print(f"❌ {len(errors)} FAILURES:")
        for e in errors:
            print(f"   {e}")
        sys.exit(1)
    else:
        print("✅ All model tests passed.")
