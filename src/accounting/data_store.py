# =============================================================================
# data_store.py — EDai Incentives Model reference data
# =============================================================================
# Data loaded from bundled JSON files. No database connection required.
#
# All reference tables are read from sql_data_cache/ at startup and held in
# memory. The public interface (variable names, DataFrame shapes, index keys)
# is identical to the original DB-backed version so that no other files need
# to change.
#
# To refresh the data from the source PostgreSQL database, run:
#   python export_to_json.py
# (requires a machine with a live DB connection and the project venv activated)
# =============================================================================

import os
import pandas as pd

# ── Path to bundled JSON cache ──────────────────────────────────────────────
_CACHE_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__),   # src/accounting/
    '..', '..', 'sql_data_cache' # → project root / sql_data_cache/
))

_DF_CACHE = {}  # in-memory cache: table_name → DataFrame


def load(table: str, **kwargs) -> pd.DataFrame:
    """
    Load a reference table from its bundled JSON file.

    Files are read once and held in _DF_CACHE; subsequent calls return a
    copy of the cached DataFrame (safe for callers that mutate in place).

    kwargs:
        columns (list): if provided, return only these columns (mirrors the
                        original sqlalchemy columns= kwarg used in data_store).
    """
    if table not in _DF_CACHE:
        json_path = os.path.join(_CACHE_DIR, table + '.json')
        if not os.path.isfile(json_path):
            raise FileNotFoundError(
                f"Reference data file not found: {json_path}\n"
                f"Run export_to_json.py to regenerate the data cache."
            )
        _DF_CACHE[table] = pd.read_json(json_path)

    df = _DF_CACHE[table].copy()

    # Honour the 'columns' kwarg that some callers pass (mirrors SQL SELECT)
    columns = kwargs.get('columns')
    if columns:
        df = df[[c for c in columns if c in df.columns]]

    return df


# =============================================================================
# Reference DataFrames — loaded and transformed at import time
# (identical transformations to the original DB-backed data_store.py)
# =============================================================================

# ── Sales apportionment ──────────────────────────────────────────────────────
sales_apportionment_df = load('20210904_Sales appportionment')
sales_apportionment_df.set_index('State', inplace=True, drop=True)

# ── Census ACS unemployment by state ─────────────────────────────────────────
census_acs_unemp_state_df = load('20210904_Census ACS 2018_Unemp state')
census_acs_unemp_state_df = census_acs_unemp_state_df[
    (census_acs_unemp_state_df.NAME != 'Geographic Area Name')
]
census_acs_unemp_state_df.set_index('NAME', inplace=True, drop=True)

census_acs_unemp_state_headings_df = load('20210904_Census ACS 2018_Unemp state_Heading legend')
census_acs_unemp_state_headings_df.set_index('Full name', inplace=True)

# ── Census ACS earnings by state ─────────────────────────────────────────────
census_acs_earn_state_df = load('20210904_Census ACS 2018_Earn State')
census_acs_earn_state_df = census_acs_earn_state_df[
    (census_acs_earn_state_df.NAME != 'Geographic Area Name')
]
census_acs_earn_state_df.set_index('NAME', inplace=True, drop=True)

census_acs_earn_state_headings_df = load('20210904_Census ACS 2018_Earn State_Heading legend')
census_acs_earn_state_headings_df.set_index('Full name', inplace=True)

# ── Discretionary incentives ─────────────────────────────────────────────────
discretionary_incentives_df = load('20210904_Discretionary Incentives')
discretionary_incentives_df = discretionary_incentives_df[
    (discretionary_incentives_df['Incentive per job'] != '')
]
discretionary_incentives_df['Incentive per job'] = (
    discretionary_incentives_df['Incentive per job']
    .apply(lambda x: str(x).replace(',', ''))
)
discretionary_incentives_df['Incentive per job'] = (
    discretionary_incentives_df['Incentive per job'].astype(float)
)

# ── Grant estimates (misc sources) ────────────────────────────────────────────
grant_estimates_misc_df = load('20210904_Grant estimates misc sources 1')
grant_estimates_misc_df.set_index('Grant', inplace=True)

# ── NAICS master crosswalk ────────────────────────────────────────────────────
naics_master_crosswalk_df = load('20210904_2017 NAICS master crosswalk')
naics_master_crosswalk_df = naics_master_crosswalk_df[
    pd.notnull(naics_master_crosswalk_df['Sectors_Census industry earnings'])
]
naics_master_crosswalk_df.set_index('Sector_Rollup IRS', inplace=True)

# ── Census industry crosswalk ─────────────────────────────────────────────────
census_industry_crosswalk_df = load('20210904_Census Industry crosswalk')
census_industry_crosswalk_df = census_industry_crosswalk_df[
    pd.notnull(census_industry_crosswalk_df['Rollup IRS sector'])
]
census_industry_crosswalk_df.set_index('Rollup IRS sector', inplace=True)

# ── BLS wages (state and county) ──────────────────────────────────────────────
bls_wages_state_df = load('20210904_BLS - Wages_State')
bls_wages_state_df.set_index('State', inplace=True)
bls_wages_state_df['Annual wages (52 weeks)'] = (
    bls_wages_state_df['Annual wages (52 weeks)']
    .apply(lambda x: float(str(x).replace('$', '').replace(',', '')))
)

bls_wages_county_df = load('20210904_BLS - Wages_County')
bls_wages_county_df.set_index('County', inplace=True)
bls_wages_county_df['Annual wages (52 weeks)'] = (
    bls_wages_county_df['Annual wages (52 weeks)']
    .apply(lambda x: float(str(x).replace('$', '').replace(',', '')))
)

# ── BLS per-capita income ──────────────────────────────────────────────────────
bls_per_capita_income_df = load('20210904_BLS Per capita income')
bls_per_capita_income_df.set_index('County', inplace=True)

# ── Census poverty by state ────────────────────────────────────────────────────
census_poverty_state_df = load('20210904_Census Poverty by State',
                                columns=['Name', 'PovPct_All Ages'])
census_poverty_state_df.set_index('Name', inplace=True)

# ── Census SUSB (state and national) ──────────────────────────────────────────
census_susb_state_df = load('20210904_Census SUSB State')
census_susb_state_df['ENTERPRISE EMPLOYMENT SIZE'] = (
    census_susb_state_df['ENTERPRISE EMPLOYMENT SIZE']
    .apply(lambda x: str(x).strip().replace('  ', ' '))
)
census_susb_state_df.set_index(
    ['STATE DESCRIPTION', 'ENTERPRISE EMPLOYMENT SIZE', 'Relevant IRS sector'],
    inplace=True
)

census_susb_national_df = load('20210904_Census SUSB National')
census_susb_national_df['ENTERPRISE EMPLOYMENT SIZE'] = (
    census_susb_national_df['ENTERPRISE EMPLOYMENT SIZE']
    .apply(lambda x: str(x).strip().replace('  ', ' '))
)

# ── Individual income taxes ────────────────────────────────────────────────────
indiv_income_taxes_df = load('20210904_Tax Found - Indiv Income Taxes')
indiv_income_taxes_df.set_index(['State', 'Brackets'], inplace=True)

# ── Census ACS industry earnings ──────────────────────────────────────────────
census_acs_industrial_heading = load('20210904_Census ACS 2018_Industry Earni_Heading legend')
census_asc_industrial_earning = load('20210904_Census ACS 2018_Industry Earni')

# ── IRS sector shares ─────────────────────────────────────────────────────────
irs_sector_shares_df = load('20210904_IRS Sector Shares')
irs_sector_shares_df['Sub-category'] = (
    irs_sector_shares_df['Sub-category']
    .apply(lambda x: str(x).strip().replace('  ', ' '))
)
irs_sector_shares_df.set_index('Sub-category', inplace=True)

# ── IRS income statement and supplementary tables ─────────────────────────────
irs_is_statements_df = load('20210904_IRS I-S Statements')
discretionary_incentives_2 = load('Discretionary Incentives Ca (2)')

# ── Special localities (counties with zone/tier designations) ─────────────────
def list_of_special_localities():
    _df = load('20210904_ List of Special Localities')
    _df.index = _df['County, State'].tolist()
    return _df

# ── Grant estimates misc #2 ────────────────────────────────────────────────────
grant_estimates_misc_2_df = load('20210904_Grant estimates misc sources 2')
grant_estimates_misc_2_df.index = grant_estimates_misc_2_df['Program'].tolist()

# ── IRS P&L supplementary tables ─────────────────────────────────────────────
irs_pl_crosswalks = load('20210904_IRS P&L_Crosswalks')
irs_pl_state_special_sector = load('20210904_IRS P&L State special sectors')

# ── NSF R&D spending ──────────────────────────────────────────────────────────
nsf_rd_spending_df = load('20210916_NSF - R&D spending')
nsf_rd_spending_df['IRS corporation categories'] = (
    nsf_rd_spending_df['IRS corporation categories']
    .apply(lambda x: str(x).strip().replace('  ', ' '))
)
nsf_rd_spending_df.set_index('IRS corporation categories', inplace=True)

# ── Special localities + county data (merged) ─────────────────────────────────
special_localities_df = load('20210904_ List of Special Localities')
special_localities_df.set_index('County, State', inplace=True)

county_data_compiled_df = load('20210904_County Data Compiled')
county_data_compiled_df.set_index('County, Abbreviation', inplace=True)

special_localities_df = special_localities_df.merge(
    county_data_compiled_df, left_index=True, right_index=True, how='inner'
)

# ── Tax Foundation: corporate income tax ──────────────────────────────────────
tax_foundation_corp_inc_tax_df = load('20210904_Tax Foundation Corp Inc Tax')
tax_foundation_corp_inc_tax_df['Rates'] = (
    tax_foundation_corp_inc_tax_df['Rates']
    .apply(lambda x: float(str(x).replace('%', '')) / 100
           if len(str(x)) > 0 and str(x) != 'None' else 0.0)
)

# ── Tax Foundation: gross receipts tax ────────────────────────────────────────
tax_foundation_corp_gross_receipts_df = load('20210904_Tax Foundation Gross Receipts')
tax_foundation_corp_gross_receipts_df.set_index('State', inplace=True)
tax_foundation_corp_gross_receipts_df['Rate to use'] = (
    tax_foundation_corp_gross_receipts_df['Rate to use']
    .apply(lambda x: float(str(x).replace('%', '')) / 100
           if len(str(x)) > 0 and str(x) != 'None' else 0.0)
)

# ── Tax Foundation: sales tax ─────────────────────────────────────────────────
tax_foundation_corp_sales_tax_df = load('20210904_Tax Foundation Sales Tax')
tax_foundation_corp_sales_tax_df['State'] = (
    tax_foundation_corp_sales_tax_df['State']
    .apply(lambda x: str(x).split('(')[0].strip())
)
tax_foundation_corp_sales_tax_df.set_index('State', inplace=True)
tax_foundation_corp_sales_tax_df['Combined Rate'] = (
    tax_foundation_corp_sales_tax_df['Combined Rate']
    .apply(lambda x: float(str(x).replace('%', '')) / 100
           if len(str(x)) > 0 and str(x) != 'None' else 0.0)
)

# ── Lincoln Institute property taxes ─────────────────────────────────────────
prop_taxes_df = load('20210905_Lincoln Inst - Prop Taxes_State output')
prop_taxes_df.set_index('State', inplace=True)
prop_taxes_df['Commercial'] = (
    prop_taxes_df['Commercial tax rate, $1M, avg. urban and rural']
    .apply(lambda x: float(str(x).replace('%', ''))
           if len(str(x)) > 0 and str(x) != 'None' else 0.0)
)
prop_taxes_df['Industrial'] = (
    prop_taxes_df['Industrial tax rate, $1M, avg. urban and rural']
    .apply(lambda x: float(str(x).replace('%', ''))
           if len(str(x)) > 0 and str(x) != 'None' else 0.0)
)

# ── State UI rates ────────────────────────────────────────────────────────────
state_ui_rates_df = load('20210904_State UI Rates',
                          columns=['Geography', 'Per FTE UI payment ($)'])
state_ui_rates_df.set_index('Geography', inplace=True)
state_ui_rates_df['Per FTE UI payment ($)'] = (
    state_ui_rates_df['Per FTE UI payment ($)']
    .apply(lambda x: float(str(x).replace('$', '').replace(',', '')))
)

# ── State-specific sectors ─────────────────────────────────────────────────────
state_specific_sector = load(
    '20210904_State-specific sectors',
    columns=['AL Property tax', 'IRS Returns of active corporations',
             'QJ qualifying industries', 'IRS Returns of active corporations']
)
state_specific_sectors_df = state_specific_sector.copy()

# ── Nebraska Advantage sectors ────────────────────────────────────────────────
ne_advantage_sectors_df = load('20210904_NE Advantage Sectors')

# ── Program descriptions ───────────────────────────────────────────────────────
descriptions_df = load('20220211_Program Descriptions')
descriptions_df.set_index(keys=['State', 'Program'], inplace=True)


# =============================================================================
# Incentive program registry — loaded from text files alongside this module
# =============================================================================

_THIS_DIR = os.path.dirname(__file__)

with open(os.path.join(_THIS_DIR, 'incentive_programs.txt'), 'r', encoding='utf8') as f:
    incentive_programs_list = f.read().strip().splitlines()

with open(os.path.join(_THIS_DIR, 'incentive_programs_types.txt'), 'r', encoding='utf8') as f:
    incentive_programs_types_list = f.read().strip().splitlines()

incentive_programs_types = {
    incentive_programs_list[i]: incentive_programs_types_list[i]
    for i in range(len(incentive_programs_list))
}

incentive_programs_by_state: dict = {}
for p in incentive_programs_list:
    state = p.split('_', 1)[0]
    program = p.split('_', 1)[1]
    if state not in incentive_programs_by_state:
        incentive_programs_by_state[state] = []
    incentive_programs_by_state[state].append(program)
