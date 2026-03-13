"""
accounting_model.py — EDai Incentives Model: public API entry point
====================================================================
Usage
-----
  from accounting.accounting_model import IncentivesInput, run_incentives_model

  result = run_incentives_model(IncentivesInput(
      archetype  = "Manufacturing",
      headcount  = 250,
      avg_wage   = 55_000,
      capex      = 10_000_000,
      state      = "Virginia",
  ))
  print(result.ebitx_margin, result.total_incentives_npv)

Archetypes
----------
  "Manufacturing"  – capital-intensive factory / industrial operation
  "Office"         – corporate headquarters / finance / back-office
  "Distribution"   – fulfilment centre / logistics hub

FastAPI compatibility
---------------------
  Both IncentivesInput and IncentivesOutput are plain dataclasses.
  Call .to_dict() on the output for JSON serialisation.
"""

from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Public data contracts
# ---------------------------------------------------------------------------

@dataclass
class IncentivesInput:
    """Inputs required to run the incentives model."""
    archetype: str           # "Manufacturing" | "Office" | "Distribution"
    headcount: int           # promised full-time jobs
    avg_wage: float          # average annual wage (USD)
    capex: float             # total capital expenditure (USD)
    state: str               # target state name, e.g. "Virginia"

    # Optional overrides / defaults
    sector: Optional[str] = None          # override archetype sector lookup
    discount_rate: float = 0.0116         # WACC for NPV calculations
    inflation_rate: float = 0.028         # annual inflation / growth rate
    home_state: str = "Arizona"           # company HQ / existing-nexus state
    home_state_sales_share: float = 0.015 # share of revenue in home state
    project_type: str = "New"             # "New" | "Expansion"


@dataclass
class ProgramResult:
    """Per-incentive-program result."""
    program: str
    eligible: bool
    incentive_type: str          # e.g. "4. Credit: Carryforward"
    incentive_category: str      # Passthrough | Carryforward math | No carryforward
    award_by_year: List[float]   # 11 elements: Year 0 (construction) + Years 1-10
    npv: float
    error: Optional[str] = None


@dataclass
class IncentivesOutput:
    """Full output returned by run_incentives_model()."""
    # Echo of key inputs
    state: str
    archetype: str
    headcount: int
    avg_wage: float
    capex: float
    sector_used: str

    # Base P&L metrics (no incentives)
    npv_sales: float
    npv_net_profit: float
    ebitx_margin: float           # net_profit NPV / sales NPV

    # Incentive programme summary
    programs_evaluated: int
    programs_eligible: int
    programs_errored: int
    total_incentives_npv: float
    post_incentive_npv: float     # net_profit NPV + total incentives NPV
    post_incentive_margin: float  # post_incentive_npv / npv_sales

    # Per-programme detail
    programs: List[ProgramResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Archetype → sector / function / commercial_or_industrial / industry_type
# ---------------------------------------------------------------------------

_ARCHETYPE_CONFIGS = {
    "Manufacturing": {
        # "Machinery manufacturing" matches the Excel benchmark sector rates
        # (COGS≈63.9%) rather than the previous default "Computer and electronic
        # product manufacturing" (COGS≈51.1%) which over-stated EBITx by ~3.7pp.
        "sector": "Machinery manufacturing",
        "function": "Capital-intensive manufacturer",
        "commercial_or_industrial": "Industrial",
        "industry_type_name": "INDUSTRIAL",
    },
    "Office": {
        "sector": "Finance and insurance total",
        "function": "Corporate headquarters",
        "commercial_or_industrial": "Commercial",
        "industry_type_name": "COMMERCIAL",
    },
    "Distribution": {
        "sector": "Transportation and warehousing total",
        "function": "Distribution center",
        "commercial_or_industrial": "Industrial",
        "industry_type_name": "DISTRIBUTION_CENTER",
    },
}

_VALID_ARCHETYPES = list(_ARCHETYPE_CONFIGS.keys())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(inp: IncentivesInput) -> List[str]:
    errors: List[str] = []
    if inp.archetype not in _VALID_ARCHETYPES:
        errors.append(
            f"archetype '{inp.archetype}' is not valid. "
            f"Choose one of: {_VALID_ARCHETYPES}"
        )
    if inp.headcount <= 0:
        errors.append(f"headcount must be > 0, got {inp.headcount}")
    if inp.avg_wage <= 0:
        errors.append(f"avg_wage must be > 0, got {inp.avg_wage}")
    if inp.capex < 0:
        errors.append(f"capex must be >= 0, got {inp.capex}")
    if not inp.state or not inp.state.strip():
        errors.append("state must not be empty")
    return errors


# ---------------------------------------------------------------------------
# Helper: safe float lookup for rates that may be a Series
# ---------------------------------------------------------------------------

def _safe_rate(val) -> float:
    """Convert a rate value (possibly a pd.Series) to float."""
    import pandas as pd
    if isinstance(val, pd.Series):
        vals = val.values.tolist()
        return float(sum(vals)) / len(vals) if vals else 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_incentives_model(inputs: IncentivesInput) -> IncentivesOutput:
    """
    Run the full incentives model for the given inputs and return a
    structured IncentivesOutput.

    Raises ValueError if inputs fail validation.
    """
    # ------------------------------------------------------------------
    # 0. Validate
    # ------------------------------------------------------------------
    errors = _validate(inputs)
    if errors:
        raise ValueError("Invalid inputs:\n" + "\n".join(f"  . {e}" for e in errors))

    warnings: List[str] = []

    # ------------------------------------------------------------------
    # 1. Import all required modules (lazy to avoid circular imports and
    #    defer heavy data_store initialisation until first call)
    # ------------------------------------------------------------------
    import pandas as pd

    from accounting.data_store import (
        incentive_programs_by_state,
        incentive_programs_types as _raw_ipt,
        sales_apportionment_df as _sa_df_raw,
        bls_wages_state_df,
        bls_wages_county_df,
        bls_per_capita_income_df,
        tax_foundation_corp_inc_tax_df,
        tax_foundation_corp_gross_receipts_df,
        tax_foundation_corp_sales_tax_df,
        prop_taxes_df,
        state_ui_rates_df,
        census_acs_earn_state_df,
        census_acs_earn_state_headings_df,
        census_acs_unemp_state_df,
        census_acs_unemp_state_headings_df,
        naics_master_crosswalk_df,
        census_industry_crosswalk_df,
        irs_sector_shares_df,
        irs_is_statements_df,
        census_susb_state_df,
        census_susb_national_df,
        census_poverty_state_df,
        special_localities_df,
        county_data_compiled_df,
        descriptions_df,
        ne_advantage_sectors_df,
        state_specific_sectors_df,
        grant_estimates_misc_df,
        grant_estimates_misc_2_df,
        discretionary_incentives_df,
        nsf_rd_spending_df,
    )
    from accounting.acs_codes import POPULATION_16_YEARS_AND_OVER
    from accounting.eligibility_calculator import get_incentive_program
    from accounting.states import STATES, abbrev_us_state
    from accounting.profit_and_loss import PNL
    from accounting.carry_forward import (
        IncentiveType,
        IncentiveCategory,
        INCENTIVE_TYPE_TO_CATEGORY_MAPPING,
        compute_carry_forward_math,
    )
    from accounting.sector_shares import (
        get_cost_of_goods_sold,
        get_other_above_the_line_costs,
        get_salaries_and_wages,
    )
    from util.capex import capex_report, IndustryType, RealProperty
    from util.personal_income_tax import PersonalIncomeTax
    from util.npv import excel_npv

    # ------------------------------------------------------------------
    # 2. Archetype -> sector / function / industry_type
    # ------------------------------------------------------------------
    cfg = _ARCHETYPE_CONFIGS[inputs.archetype]
    sector = inputs.sector if inputs.sector else cfg["sector"]
    function_type = cfg["function"]
    commercial_or_industrial = cfg["commercial_or_industrial"]
    itn = cfg["industry_type_name"]
    if itn == "COMMERCIAL":
        industry_type = IndustryType.COMMERCIAL
    elif itn == "DISTRIBUTION_CENTER":
        industry_type = IndustryType.DISTRIBUTION_CENTER
    else:
        industry_type = IndustryType.INDUSTRIAL

    # ------------------------------------------------------------------
    # 3. Validate state is in programme registry
    # ------------------------------------------------------------------
    target_state = inputs.state.strip()
    if target_state not in incentive_programs_by_state:
        raise ValueError(
            f"State '{target_state}' has no incentive programmes registered. "
            f"Check spelling -- must match keys in incentive_programs_by_state."
        )

    # ------------------------------------------------------------------
    # 4. Incentive type / category dicts (convert raw strings to enums)
    # ------------------------------------------------------------------
    incentive_programs_types_enum = {
        k: IncentiveType.from_str(v) for k, v in _raw_ipt.items()
    }
    incentive_programs_categories = {
        k: INCENTIVE_TYPE_TO_CATEGORY_MAPPING[v]
        for k, v in incentive_programs_types_enum.items()
    }

    # ------------------------------------------------------------------
    # 5. Sales apportionment population weights + tax incidence
    #    (replicates main.py lines 108-292)
    # ------------------------------------------------------------------
    sa_df = _sa_df_raw.copy()
    census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER] = (
        census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER].astype(float)
    )
    total_population = census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER].sum()

    sa_df['Population 16+ Years'] = [
        census_acs_unemp_state_df.loc[s][POPULATION_16_YEARS_AND_OVER]
        for s in sa_df.index.values
    ]
    sa_df['Share'] = sa_df['Population 16+ Years'].apply(lambda x: x / total_population)

    home_state_population = sa_df.loc[inputs.home_state]['Population 16+ Years']
    remainder = 1.0 - inputs.home_state_sales_share

    state_to_manual_share_of_sales = {
        state: inputs.home_state_sales_share if state == inputs.home_state
        else float(
            sa_df.loc[state]['Population 16+ Years']
            / (total_population - home_state_population)
            * remainder
        )
        for state in sa_df.index.values.tolist()
    }

    # Apportionment weights (Sales / Payroll / Property) by approach type
    _approach_to_weights = {
        'Evenly weighted three factors':                              (0.33, 0.33, 0.33),
        'Double weighted sales factor':                               (0.5,  0.25, 0.25),
        'Triple weighted sales factor':                               (0.6,  0.2,  0.2),
        'Single factor apportionment (sales)':                        (1.0,  0,    0),
        'No state income tax':                                        (0,    0,    0),
        'Custom apportionment (Single in 2022; assumed 2022)':        (1.0,  0,    0),
        'Single factor apportionment (sales) but may vay by industry':(0.5,  0.25, 0.25),
    }
    sa_df['Sales']   = sa_df['Approach used'].apply(
        lambda x: _approach_to_weights.get(x, (0.5, 0.25, 0.25))[0]
    )
    sa_df['Payroll'] = sa_df['Approach used'].apply(
        lambda x: _approach_to_weights.get(x, (0.5, 0.25, 0.25))[1]
    )
    sa_df['Property'] = sa_df['Approach used'].apply(
        lambda x: _approach_to_weights.get(x, (0.5, 0.25, 0.25))[2]
    )
    sa_df['Est. home state sales'] = sa_df['Share'].copy()

    tax_incidence = []
    for state in sa_df.index.tolist():
        r = sa_df.loc[state]
        tax_incidence.append(
            r['Sales'] * state_to_manual_share_of_sales.get(state, 0.0)
            + r['Payroll'] * 1.0
            + r['Property'] * 1.0
        )
    sa_df['Tax incidence (Portion of sales to be taxed)'] = tax_incidence

    # ------------------------------------------------------------------
    # 6. Unemployment / poverty / income lookup dicts
    # ------------------------------------------------------------------
    unemployment_rate_table_code = census_acs_unemp_state_headings_df.loc[
        'Percent Estimate!!EMPLOYMENT STATUS!!Population 16 years and over!!'
        'In labor force!!Civilian labor force!!Unemployed'
    ]['Table code']

    state_to_unemployment_rate = {
        state: float(census_acs_unemp_state_df.loc[state][unemployment_rate_table_code]) / 100
        for state in STATES
    }

    county_to_unemployment_rate_raw = {
        county: float(special_localities_df.loc[county]['Unemployment, 2019']) / 100
        for county in special_localities_df[
            special_localities_df['Unemployment, 2019'] != ''
        ].index.values.tolist()
    }

    def _format_county(county: str) -> str:
        abbr = county.split(',')[-1].strip()
        full = abbrev_us_state.get(abbr, abbr)
        return county.replace(abbr, full)

    county_to_unemployment_rate = {
        _format_county(k): v
        for k, v in county_to_unemployment_rate_raw.items()
    }

    state_to_per_capita_income = {}
    for state in STATES:
        try:
            raw = bls_per_capita_income_df.loc[state]['2018']
            if isinstance(raw, pd.Series):
                raw = raw.iloc[0]
            state_to_per_capita_income[state] = float(
                str(raw).replace(',', '').replace('$', '').strip()
            )
        except (KeyError, ValueError):
            state_to_per_capita_income[state] = 0.0

    county_to_per_capita_income = {}
    for county in bls_per_capita_income_df[
        bls_per_capita_income_df['2018'] != ''
    ].index.values.tolist():
        v = bls_per_capita_income_df.loc[county]['2018']
        try:
            if isinstance(v, pd.Series):
                v = float(v.apply(
                    lambda x: float(str(x).replace(',', '').replace('$', '').strip())
                ).mean())
            else:
                v = float(str(v).replace(',', '').replace('$', '').strip())
            county_to_per_capita_income[county] = v
        except (ValueError, TypeError):
            pass

    state_to_poverty_rate = {}
    for state in STATES:
        try:
            state_to_poverty_rate[state] = float(
                census_poverty_state_df.loc[state]['PovPct_All Ages']
            )
        except KeyError:
            state_to_poverty_rate[state] = 0.0

    # ------------------------------------------------------------------
    # 7. Wage dicts
    # ------------------------------------------------------------------
    prevailing_wages_state = {
        state: float(bls_wages_state_df.loc[state]['Annual wages (52 weeks)'])
        for state in STATES
    }
    prevailing_wages_county = {
        county: float(bls_wages_county_df.loc[county]['Annual wages (52 weeks)'])
        for county in bls_wages_county_df.index.values.tolist()
    }

    # ------------------------------------------------------------------
    # 8. Sector-level derived inputs
    # ------------------------------------------------------------------
    try:
        rollup_irs_sector = nsf_rd_spending_df.loc[sector]['Rollup IRS sector']
        if isinstance(rollup_irs_sector, pd.Series):
            rollup_irs_sector = rollup_irs_sector.iloc[0]
    except KeyError:
        rollup_irs_sector = sector
        warnings.append(f"nsf_rd_spending_df lookup failed for sector '{sector}'.")

    try:
        census_industry_earnings_name = census_industry_crosswalk_df.loc[
            rollup_irs_sector
        ]['Geographic Area Name']
        if isinstance(census_industry_earnings_name, pd.Series):
            census_industry_earnings_name = census_industry_earnings_name.iloc[0]
    except KeyError:
        census_industry_earnings_name = "Total"
        warnings.append(f"census_industry_crosswalk_df lookup failed for '{rollup_irs_sector}'.")

    try:
        manual_rd_share_of_sales = float(
            nsf_rd_spending_df.loc[sector]['Manual R&D share of sales']
        ) / 100
    except (KeyError, TypeError):
        manual_rd_share_of_sales = 0.03
        warnings.append("R&D share lookup failed; defaulting to 3%.")

    costs_of_goods_sold = get_cost_of_goods_sold(sector)
    other_above_the_line_costs = get_other_above_the_line_costs(sector) - manual_rd_share_of_sales
    salaries_and_wages_rate = get_salaries_and_wages(sector)

    # Promised jobs range (mirroring main.py)
    jobs = inputs.headcount
    if jobs < 5:
        promised_jobs_range = '02: 0-4'
    elif jobs < 10:
        promised_jobs_range = '03: 5-9'
    elif jobs < 20:
        promised_jobs_range = '04: 10-19'
    elif jobs < 100:
        promised_jobs_range = '06: 20-99'
    elif jobs < 500:
        promised_jobs_range = '07: 100-499'
    else:
        promised_jobs_range = '09: 500+'

    # Average implied sales from national SUSB data
    try:
        avg_implied_sales = float(
            census_susb_national_df[
                (census_susb_national_df['ENTERPRISE EMPLOYMENT SIZE'] == promised_jobs_range)
                & (census_susb_national_df['Relevant IRS sector'] == rollup_irs_sector)
            ]['Avg. implied sales'].astype(float).sum()
        )
        if avg_implied_sales == 0.0:
            raise ValueError("zero result")
    except Exception:
        avg_implied_sales = inputs.avg_wage * inputs.headcount * 3
        warnings.append(
            f"SUSB national avg_implied_sales lookup failed "
            f"(jobs_range='{promised_jobs_range}', sector='{rollup_irs_sector}'); "
            f"using wage x headcount x 3."
        )

    # High-level category
    try:
        high_level_category = irs_sector_shares_df.loc[sector]['Category']
        if isinstance(high_level_category, pd.Series):
            high_level_category = high_level_category.iloc[0]
    except KeyError:
        high_level_category = 'Manufacturing'

    # ------------------------------------------------------------------
    # 9. State-level rate lookups
    # ------------------------------------------------------------------
    tax_foundation_corp_inc_tax_df_grouped = (
        tax_foundation_corp_inc_tax_df[['State', 'Rates']].groupby('State').max()
    )
    states_to_state_corporate_income_tax_rates = {}
    for state in STATES:
        if state in tax_foundation_corp_inc_tax_df_grouped.index:
            states_to_state_corporate_income_tax_rates[state] = _safe_rate(
                tax_foundation_corp_inc_tax_df_grouped.loc[state]['Rates']
            )
        else:
            states_to_state_corporate_income_tax_rates[state] = 0.0

    states_to_state_corporate_income_tax_apportionment = {
        state: _safe_rate(sa_df.loc[state]['Tax incidence (Portion of sales to be taxed)'])
        if state in sa_df.index else 1.0
        for state in STATES
    }

    # Census earnings share of sales by sector per state
    try:
        earnings_col_code = census_acs_earn_state_headings_df.loc[
            census_industry_earnings_name
        ]['Table code']
        if isinstance(earnings_col_code, pd.Series):
            earnings_col_code = earnings_col_code.iloc[0]
        us_total = float(census_acs_earn_state_df.loc["United States"][earnings_col_code])
        states_to_share_of_sales_by_sector = {
            state: float(census_acs_earn_state_df.loc[state][earnings_col_code]) / us_total
            if us_total else 1.0
            for state in STATES
        }
    except (KeyError, TypeError, ZeroDivisionError):
        states_to_share_of_sales_by_sector = {state: 1.0 for state in STATES}
        warnings.append("Census earnings share-of-sales lookup failed; defaulting to 1.0.")

    def _state_rates(state):
        pt  = _safe_rate(prop_taxes_df.loc[state][commercial_or_industrial]
                         if state in prop_taxes_df.index else 0.0)
        grt = _safe_rate(tax_foundation_corp_gross_receipts_df.loc[state]['Rate to use']
                         if state in tax_foundation_corp_gross_receipts_df.index else 0.0)
        ui  = _safe_rate(state_ui_rates_df.loc[state]['Per FTE UI payment ($)']
                         if state in state_ui_rates_df.index else 0.0)
        st  = _safe_rate(tax_foundation_corp_sales_tax_df.loc[state]['Combined Rate']
                         if state in tax_foundation_corp_sales_tax_df.index else 0.0)
        cit = states_to_state_corporate_income_tax_rates.get(state, 0.0)
        app = states_to_state_corporate_income_tax_apportionment.get(state, 1.0)
        sw  = states_to_share_of_sales_by_sector.get(state, 1.0)
        return pt, grt, ui, st, cit, app, sw

    # ------------------------------------------------------------------
    # 10. Build capex object
    # ------------------------------------------------------------------
    federal_income_tax = 0.21
    total_equipment_share_of_sales = 0.25
    capex_obj = capex_report(inputs.capex)

    def _make_pnl(state):
        pt, grt, ui, st, cit, app, sw = _state_rates(state)
        return PNL(
            capex=capex_obj,
            sales=avg_implied_sales,
            costs_of_goods_sold_rate=costs_of_goods_sold,
            salaries_and_wages_adjuster=sw,
            salaries_and_wages_rate=salaries_and_wages_rate,
            research_and_development_rate=manual_rd_share_of_sales,
            other_above_the_line_costs_rate=other_above_the_line_costs,
            federal_income_tax_rate=federal_income_tax,
            inflation_rate=inputs.inflation_rate,
            state_corporate_income_tax_apportionment=app,
            state_corporate_income_tax_rate=cit,
            state_ui_tax_amount=ui,
            state_local_sales_tax_rate=st,
            gross_receipts_tax_rate=grt,
            property_tax_rate=pt,
            num_jobs=inputs.headcount,
            discount_rate=inputs.discount_rate,
            industry_type=industry_type,
            total_equipment_share_of_sales=total_equipment_share_of_sales,
        )

    def _make_pnl_inputs(state):
        pt, grt, ui, st, cit, app, sw = _state_rates(state)
        return dict(
            capex=capex_obj,
            sales=avg_implied_sales,
            costs_of_goods_sold_rate=costs_of_goods_sold,
            salaries_and_wages_adjuster=sw,
            salaries_and_wages_rate=salaries_and_wages_rate,
            research_and_development_rate=manual_rd_share_of_sales,
            other_above_the_line_costs_rate=other_above_the_line_costs,
            federal_income_tax_rate=federal_income_tax,
            inflation_rate=inputs.inflation_rate,
            state_corporate_income_tax_apportionment=app,
            state_corporate_income_tax_rate=cit,
            state_ui_tax_amount=ui,
            state_local_sales_tax_rate=st,
            gross_receipts_tax_rate=grt,
            property_tax_rate=pt,
            num_jobs=inputs.headcount,
            discount_rate=inputs.discount_rate,
            industry_type=industry_type,
            total_equipment_share_of_sales=total_equipment_share_of_sales,
        )

    # Build target-state PNL for headline metrics
    target_pnl = _make_pnl(target_state)
    npv_sales = target_pnl.npv_sales
    npv_net_profit = target_pnl.npv_net_profit

    # EBITx is reported on a pre-GRT basis to match the Excel benchmark
    # convention.  Gross Receipts Tax (e.g. Arizona TPT at 5.6%) is a
    # revenue-based levy that the Excel model excludes from the EBITx margin
    # line — it is still included in the per-programme PNL inputs used for
    # incentive calculations.  For states with no GRT (e.g. Alabama) this
    # add-back is zero and has no effect.
    npv_grt = excel_npv(
        inputs.discount_rate,
        target_pnl.npv_dicts['Gross receipts tax'][1:],  # skip Year-0 stub
    )
    ebitx_margin = (npv_net_profit + npv_grt) / npv_sales if npv_sales else 0.0

    # ------------------------------------------------------------------
    # 11. Workforce / discretionary / zone dicts
    # ------------------------------------------------------------------
    workforce_programs_ipj_map = {
        program: float(grant_estimates_misc_df.loc[program]['Amount'])
        for program in grant_estimates_misc_df.index.values.tolist()
    }

    discretionary_incentives_groups = (
        discretionary_incentives_df[['Program', 'Incentive per job']].groupby('Program')
    )

    zone_type_1 = {
        county: special_localities_df.loc[county]['Zone Type 1']
        for county in special_localities_df.index.values.tolist()
    }
    zone_type_2 = {
        county: special_localities_df.loc[county]['Zone Type 2']
        for county in special_localities_df.index.values.tolist()
    }
    zone_type_3 = {
        county: special_localities_df.loc[county]['Zone Type 3']
        for county in special_localities_df.index.values.tolist()
    }
    county_drop_down_list = ["Catron County, NM"]

    # ------------------------------------------------------------------
    # 12. Project level inputs
    # ------------------------------------------------------------------
    project_level_inputs = {
        'Attraction or Expansion?': 'Relocation' if inputs.project_type == 'New' else 'Expansion',
        'IRS Sector': sector,
        'Project type': inputs.project_type,
        'High-level category': high_level_category,
        'Project category': function_type,
        'Rollup IRS sector': rollup_irs_sector,
        'Promised jobs': inputs.headcount,
        'Promised jobs range for state-sector sales estimates': promised_jobs_range,
        'Promised capital investment': inputs.capex,
        'Promised wages': inputs.avg_wage,
        'P&L Salary state adjuster (on/off)': 'IRS_AdjByState',
        'Wages as share of total compensation (manuf. vs. services)':
            0.664 if high_level_category == 'Manufacturing' else 0.707,
        'Census industry earnings name': census_industry_earnings_name,
        'Industry median earnings (Census)':
            'Commercial' if function_type in ['Corporate headquarters', 'Call center']
            else 'Industrial',
        'Calculated estimated sales based on national data': avg_implied_sales,
        'Estimated sales based on national data (currently used; estimate or manual input)':
            avg_implied_sales,
        'Prevailing wages county': prevailing_wages_county,
        'Estimated sales based on state data (not used)': {},
        'Prevailing wages': prevailing_wages_state,
        'Equivalent payroll': {
            state: prevailing_wages_state[state] * inputs.headcount
            for state in STATES
        },
        'Equivalent payroll (BASE)': inputs.avg_wage * inputs.headcount,
        'Federal minimum wage': 7.25,
        'State personal income tax': {
            state: PersonalIncomeTax(inputs.avg_wage, state).tax_rate()
            for state in STATES
        },
        'Discount rate': inputs.discount_rate,
        'Inflation (employment cost index)': inputs.inflation_rate,
    }

    # ------------------------------------------------------------------
    # 13. Build all_inputs_per_state (needed by some multi-state programmes)
    # ------------------------------------------------------------------
    _base_shared = {
        'project_level_inputs': project_level_inputs,
        'state_to_unemployment_rate': state_to_unemployment_rate,
        'state_to_poverty_rate': state_to_poverty_rate,
        'state_to_per_capita_income': state_to_per_capita_income,
        'state_to_prevailing_wages': prevailing_wages_state,
        'county_to_prevailing_wages': prevailing_wages_county,
        'county_to_unemployment_rate': county_to_unemployment_rate,
        'county_overrides': {},
        'county_to_per_capita_income': county_to_per_capita_income,
        'workforce_programs_ipj_map': workforce_programs_ipj_map,
        'discretionary_incentives_groups': discretionary_incentives_groups,
        'sales_apportionment_df': sa_df,
        'state_to_manual_share_of_sales': state_to_manual_share_of_sales,
        'county_drop_down_list': county_drop_down_list,
        'zone_type_1': zone_type_1,
        'zone_type_2': zone_type_2,
        'zone_type_3': zone_type_3,
        'capex': capex_obj,
    }

    all_inputs_per_state = {}
    for state in STATES:
        _pi = _make_pnl_inputs(state)
        _p  = PNL(**_pi)
        entry = dict(_base_shared)
        entry['pnl'] = _p
        entry['pnl_inputs'] = _pi
        all_inputs_per_state[state] = entry

    # ------------------------------------------------------------------
    # 14. Evaluate all programmes for the target state
    # ------------------------------------------------------------------
    program_results: List[ProgramResult] = []
    total_incentives_npv = 0.0

    state_programs = incentive_programs_by_state.get(target_state, [])
    all_inputs_target = dict(all_inputs_per_state[target_state])
    all_inputs_target['all_inputs_per_state'] = all_inputs_per_state

    for prog_name in state_programs:
        full_key = f"{target_state}_{prog_name}"
        inc_type_enum = incentive_programs_types_enum.get(
            full_key, IncentiveType.NOT_APPLICABLE
        )
        inc_cat_enum = incentive_programs_categories.get(
            full_key, IncentiveCategory.NO_CARRYFORWARD
        )
        type_str = inc_type_enum.value
        cat_str = inc_cat_enum.value

        if inc_type_enum == IncentiveType.NOT_APPLICABLE:
            program_results.append(ProgramResult(
                program=prog_name,
                eligible=False,
                incentive_type=type_str,
                incentive_category=cat_str,
                award_by_year=[0.0] * 11,
                npv=0.0,
                error="Not modelled (n/a)",
            ))
            continue

        try:
            prog_instance = get_incentive_program(
                target_state, prog_name, **all_inputs_target
            )

            eligible = prog_instance.estimated_eligibility()
            raw_awards = prog_instance.estimated_incentives() if eligible else [0.0] * 11

            # Some state modules return a defaultdict/dict with a 'value' key
            # rather than a plain list.  list(dict) gives the keys (strings),
            # which would crash excel_npv.  Extract the numeric 'value' list
            # and coerce any sentinel strings ("Base", "-") to 0.0.
            if isinstance(raw_awards, dict):
                raw_list = list(raw_awards.get('value', []))
            else:
                raw_list = list(raw_awards)

            def _to_float(x):
                try:
                    return float(x)
                except (TypeError, ValueError):
                    return 0.0

            raw_list = [_to_float(x) for x in raw_list]
            awards = raw_list + [0.0] * max(0, 11 - len(raw_list))
            awards = awards[:11]

            prog_npv = excel_npv(inputs.discount_rate, awards[1:]) if eligible else 0.0

            program_results.append(ProgramResult(
                program=prog_name,
                eligible=eligible,
                incentive_type=type_str,
                incentive_category=cat_str,
                award_by_year=awards,
                npv=prog_npv,
            ))

            if eligible:
                total_incentives_npv += prog_npv

        except ModuleNotFoundError as exc:
            program_results.append(ProgramResult(
                program=prog_name,
                eligible=False,
                incentive_type=type_str,
                incentive_category=cat_str,
                award_by_year=[0.0] * 11,
                npv=0.0,
                error=f"Module not found: {exc}",
            ))
        except Exception as exc:
            program_results.append(ProgramResult(
                program=prog_name,
                eligible=False,
                incentive_type=type_str,
                incentive_category=cat_str,
                award_by_year=[0.0] * 11,
                npv=0.0,
                error=f"{type(exc).__name__}: {exc}",
            ))

    # ------------------------------------------------------------------
    # 15. Aggregate and return
    # ------------------------------------------------------------------
    eligible_programs = [p for p in program_results if p.eligible]
    errored_programs  = [
        p for p in program_results
        if p.error and p.error != "Not modelled (n/a)"
    ]

    # Use pre-GRT net profit for the post-incentive sticker (consistent with
    # ebitx_margin definition above and the Excel benchmark convention).
    post_incentive_npv    = (npv_net_profit + npv_grt) + total_incentives_npv
    post_incentive_margin = post_incentive_npv / npv_sales if npv_sales else 0.0

    return IncentivesOutput(
        state=target_state,
        archetype=inputs.archetype,
        headcount=inputs.headcount,
        avg_wage=inputs.avg_wage,
        capex=inputs.capex,
        sector_used=sector,
        npv_sales=npv_sales,
        npv_net_profit=npv_net_profit,
        ebitx_margin=ebitx_margin,
        programs_evaluated=len(program_results),
        programs_eligible=len(eligible_programs),
        programs_errored=len(errored_programs),
        total_incentives_npv=total_incentives_npv,
        post_incentive_npv=post_incentive_npv,
        post_incentive_margin=post_incentive_margin,
        programs=program_results,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# __main__ -- Virginia test case
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test = IncentivesInput(
        archetype  = "Manufacturing",
        headcount  = 250,
        avg_wage   = 55_000,
        capex      = 10_000_000,
        state      = "Virginia",
    )

    print("=" * 68)
    print("EDai Incentives Model -- Virginia / Manufacturing / 250 jobs")
    print("=" * 68)

    result = run_incentives_model(test)

    print(f"\n-- Base P&L --")
    print(f"  NPV Sales:            ${result.npv_sales:>18,.0f}")
    print(f"  NPV Net Profit:       ${result.npv_net_profit:>18,.0f}")
    print(f"  EBITx margin:         {result.ebitx_margin:>18.2%}")

    print(f"\n-- Incentives Summary --")
    print(f"  Programmes evaluated:  {result.programs_evaluated}")
    print(f"  Programmes eligible:   {result.programs_eligible}")
    print(f"  Programmes errored:    {result.programs_errored}")
    print(f"  Total incentives NPV: ${result.total_incentives_npv:>18,.0f}")
    print(f"  Post-incentive NPV:   ${result.post_incentive_npv:>18,.0f}")
    print(f"  Post-incentive margin: {result.post_incentive_margin:>18.2%}")

    print(f"\n-- Eligible Programmes --")
    eligible = [p for p in result.programs if p.eligible]
    if eligible:
        for p in eligible:
            print(f"  OK  {p.program:<52}  NPV: ${p.npv:>12,.0f}  [{p.incentive_type}]")
    else:
        print("  (none)")

    print(f"\n-- Errored Programmes (first 10) --")
    errored = [p for p in result.programs if p.error and p.error != "Not modelled (n/a)"]
    if errored:
        for p in errored[:10]:
            print(f"  ERR  {p.program:<50}  {p.error[:65]}")
        if len(errored) > 10:
            print(f"       ... and {len(errored) - 10} more")
    else:
        print("  (none)")

    if result.warnings:
        print(f"\n-- Warnings --")
        for w in result.warnings:
            print(f"  WARN  {w}")

    print("\n" + "=" * 68)
