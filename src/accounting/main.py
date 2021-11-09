from accounting.data_store import *
from accounting.acs_codes import POPULATION_16_YEARS_AND_OVER
import json
from accounting.eligibility_calculator import get_incentive_program
from util.capex import capex_report, IndustryType
from util.personal_income_tax import PersonalIncomeTax
from accounting.sector_shares import get_cost_of_goods_sold, get_other_above_the_line_costs, get_salaries_and_wages
from accounting.states import STATES
from accounting.profit_and_loss import PNL


DEBUG = True

# TODO pull from DB
federal_income_tax = 0.1323
federal_minimum_wage = 7.25

inputs_county_overrides = {

}

inputs_basic = {
    'Sector': 'Computer and electronic product manufacturing',
    'Function': 'Capital-intensive manufacturer',
    'Promised jobs': 2061,
    'Promised capital investment': 380000000,
    'Promised wages': 119000,
    'Project Type': 'New'
}

inputs_adjustable = {
    'P&L Salary state adjuster (on/off)': 'IRS_AdjByState',
    'Estimated sales based on national data': 1844456989,
    'Discount rate': 0.0116,
    'Inflation type': 'Employment cost index',
    'Inflation': 0.028
}

inputs_home_state_sales_apportionment = {
    'Home state': 'Arizona',
    'Scenario': 'Manual',
    'Home state sales share': 0.015,
}

inputs_discretionary_incentives_amounts = {
    'Incentives per job (IPJ) figure to use': 'Median IPJ'
}

inputs_workforce_programs = {
    'Incentives per job (IPJ) figure to use': 'Calculated IPJ'
}

commercial_or_industrial = ('Commercial'
                        if inputs_basic['Function'] in ['Corporate headquarters', 'Call center']
                        else 'Industrial')

industry_type = IndustryType.COMMERCIAL if commercial_or_industrial == 'Commercial' else IndustryType.INDUSTRIAL

inputs_capex_schedule = {
    'Total capex': inputs_basic['Promised capital investment'],
    'Automatic capex': commercial_or_industrial,
    'Capex breakout': 'Automatic capex'
}

# Sales apportionment calcs
census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER] = census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER].astype(float)
total_population = census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER].sum()

unemployment_rate_table_code = census_acs_unemp_state_headings_df.loc['Percent Estimate!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force!!Civilian labor force!!Unemployed']['Table code']

state_to_unemployment_rate = {
    state: float(census_acs_unemp_state_df.loc[state][unemployment_rate_table_code])/100
    for state in STATES
}

county_to_unemployment_rate = {
    county: float(special_localities_df.loc[county]['Unemployment, 2019']) / 100
    for county in special_localities_df[special_localities_df['Unemployment, 2019']!=''].index.values.tolist()
}

state_to_per_capita_income = {
    state: float(bls_per_capita_income_df.loc[state]['2018'].replace(',','').replace('$', '').strip())
    for state in STATES
}

county_to_per_capita_income = {}
for county in bls_per_capita_income_df[bls_per_capita_income_df['2018'] != ''].index.values.tolist():
    v = bls_per_capita_income_df.loc[county]['2018']
    if isinstance(v, pd.Series):
        v = float(v.apply(lambda x: float(x.replace(',', '').replace('$', '').strip())).mean())
    else:
        v = float(v.replace(',', '').replace('$', '').strip())
    county_to_per_capita_income[county] = v

state_to_poverty_rate = {
    state: float(census_poverty_state_df.loc[state]['PovPct_All Ages'])
    for state in STATES
}

sales_apportionment_df['Population 16+ Years'] = [census_acs_unemp_state_df.loc[s][POPULATION_16_YEARS_AND_OVER] for s in sales_apportionment_df.index.values]
sales_apportionment_df['Share'] = sales_apportionment_df['Population 16+ Years'].apply(lambda x: x/total_population)

inputs_home_state_sales_apportionment['Total 16+ population'] = total_population
inputs_home_state_sales_apportionment['Population share'] = sales_apportionment_df.loc[inputs_home_state_sales_apportionment['Home state']]['Share']
inputs_home_state_sales_apportionment['Home state population'] = sales_apportionment_df.loc[inputs_home_state_sales_apportionment['Home state']]['Population 16+ Years']
inputs_home_state_sales_apportionment['Remainder'] = \
    1.0 - inputs_home_state_sales_apportionment['Home state sales share']

state_to_manual_share_of_sales = {
    state: inputs_home_state_sales_apportionment['Home state sales share'] if state == inputs_home_state_sales_apportionment['Home state'] \
    else sales_apportionment_df.loc[state]['Population 16+ Years']/(total_population-inputs_home_state_sales_apportionment['Home state population'])
    for state in sales_apportionment_df.index.values.tolist()
}

approach_to_weights = {
    'Evenly weighted three factors': (0.33, 0.33, 0.33),
    'Double weighted sales factor': (0.5, 0.25, 0.25),
    'Triple weighted sales factor': (0.6, 0.2, 0.2),
    'Single factor apportionment (sales)': (1.0, 0, 0),
    'No state income tax': (0, 0, 0),
    'Custom apportionment (Single in 2022; assumed 2022)': (1.0, 0, 0),
    'Single factor apportionment (sales) but may vay by industry': (0.5, 0.25, 0.25)
}
sales_apportionment_df['Sales'] = sales_apportionment_df['Approach used'].apply(lambda x: approach_to_weights[x][0])
sales_apportionment_df['Payroll'] = sales_apportionment_df['Approach used'].apply(lambda x: approach_to_weights[x][1])
sales_apportionment_df['Property'] = sales_apportionment_df['Approach used'].apply(lambda x: approach_to_weights[x][2])

sales_apportionment_df['Est. home state sales'] = sales_apportionment_df['Share'].copy()
tax_incidence = []
for state in sales_apportionment_df.index.tolist():
    r = sales_apportionment_df.loc[state]
    tax_incidence.append(
        r['Sales'] * state_to_manual_share_of_sales[state] +
        r['Payroll'] * 1.0 +
        r['Property'] * 1.0
    )
sales_apportionment_df['Tax incidence (Portion of sales to be taxed)'] = tax_incidence

# Incentives calcs
discretionary_incentives_groups = discretionary_incentives_df[['Program', 'Incentive per job']].groupby('Program')

# Workforce programs
workforce_programs_ipj_map = {
    program: float(grant_estimates_misc_df.loc[program]['Amount'])
    for program in grant_estimates_misc_df.index.values.tolist()
}

promised_jobs = inputs_basic['Promised jobs']
if promised_jobs < 5:
    promised_jobs_range = '02: 0-4'
elif promised_jobs < 10:
    promised_jobs_range = '03: 5-9'
elif promised_jobs < 20:
    promised_jobs_range = '04: 10-19'
elif promised_jobs < 100:
    promised_jobs_range = '05: 20-99'
elif promised_jobs < 500:
    promised_jobs_range = '06: 100-499'
else:
    promised_jobs_range = '09: 500+'

high_level_category = irs_sector_shares_df.loc[inputs_basic['Sector']]['Category']
rollup_irs_sector = nsf_rd_spending_df.loc[inputs_basic['Sector']]['Rollup IRS sector']
census_industry_earnings_name = census_industry_crosswalk_df.loc[rollup_irs_sector]['Geographic Area Name']

# PNL Inputs
manual_rd_share_of_sales = float(nsf_rd_spending_df.loc[inputs_basic['Sector']]['Manual R&D share of sales'])/100
other_above_the_line_costs = get_other_above_the_line_costs(inputs_basic['Sector']) - manual_rd_share_of_sales
costs_of_goods_sold = get_cost_of_goods_sold(inputs_basic['Sector'])

states_to_state_corporate_income_tax_apportionment = {
    state: sales_apportionment_df.loc[state]['Tax incidence (Portion of sales to be taxed)']
    for state in STATES
}

tax_foundation_corp_inc_tax_df_grouped = tax_foundation_corp_inc_tax_df[['State', 'Rates']].groupby('State').max()

states_to_state_corporate_income_tax_rates = {
    state: tax_foundation_corp_inc_tax_df_grouped.loc[state]['Rates']
    for state in STATES
}

states_to_share_of_sales_by_sector = {
    state: float(census_acs_earn_state_df.loc[state][census_acs_earn_state_headings_df.loc[census_industry_earnings_name]['Table code']]) \
    / float(census_acs_earn_state_df.loc["United States"][census_acs_earn_state_headings_df.loc[census_industry_earnings_name]['Table code']])
    for state in STATES
}

avg_implied_sales = census_susb_national_df[
    (census_susb_national_df['ENTERPRISE EMPLOYMENT SIZE']==promised_jobs_range)
    &(census_susb_national_df['Relevant IRS sector']==rollup_irs_sector)
]['Avg. implied sales'].astype(float).sum()

prevailing_wages_state = {
    state: float(bls_wages_state_df.loc[state]['Annual wages (52 weeks)'])
    for state in STATES
}

prevailing_wages_county = {
    county: float(bls_wages_county_df.loc[county]['Annual wages (52 weeks)'])
    for county in bls_wages_county_df.index.values.tolist()
}


# Project level inputs
project_level_inputs = {
    'Attraction or Expansion?': 'Relocation' if inputs_basic['Project Type'] == 'New' else 'Expansion',
    'IRS Sector': inputs_basic['Sector'],
    'High-level category': high_level_category,
    'Project category': inputs_basic['Function'],
    'Rollup IRS sector': rollup_irs_sector,
    'Promised jobs': inputs_basic['Promised jobs'],
    'Promised jobs range for state-sector sales estimates': promised_jobs_range,
    'Promised capital investment': inputs_basic['Promised capital investment'],
    'Promised wages': inputs_basic['Promised wages'],
    'P&L Salary state adjuster (on/off)': inputs_adjustable['P&L Salary state adjuster (on/off)'],
    'Wages as share of total compensation (manuf. vs. services)': \
    0.664 if high_level_category == 'Manufacturing' else 0.707,
    'Census industry earnings name': census_industry_earnings_name,
    'Industry median earnings (Census)': 'Commercial' if inputs_basic['Function'] in ['Corporate headquarters', 'Call center'] else 'Industrial',
    'Calculated estimated sales based on national data': avg_implied_sales,
    'Estimated sales based on national data (currently used; estimate or manual input)': inputs_adjustable['Estimated sales based on national data'],
    'Estimated sales based on state data (not used)': {
        state: census_susb_state_df.loc[state, promised_jobs_range, rollup_irs_sector]['Avg. implied sales'].astype(float).sum()
        for state in STATES
    },
    'Prevailing wages': prevailing_wages_state,
    'Equivalent payroll': {
        state: prevailing_wages_state[state] * promised_jobs
        for state in STATES
    },
    'Equivalent payroll (BASE)': inputs_basic['Promised wages'] * promised_jobs,
    'Federal minimum wage': federal_minimum_wage,
    'State personal income tax': {
        state: PersonalIncomeTax(inputs_basic['Promised wages'], state).tax_rate()
        for state in STATES
    },
    'Discount rate': inputs_adjustable['Discount rate'],
    'Inflation (employment cost index)': inputs_adjustable['Inflation'],
}

# Capex
capex = capex_report(inputs_capex_schedule['Total capex'])

all_inputs = {
    'capex': capex,
    'project_level_inputs': project_level_inputs,
    # State socioeconomic factors
    'state_to_unemployment_rate': state_to_unemployment_rate,
    'county_to_unemployment_rate': county_to_unemployment_rate,
    'state_to_per_capita_income': state_to_per_capita_income,
    'county_to_per_capita_income': county_to_per_capita_income,
    'state_to_prevailing_wages': prevailing_wages_state,
    'county_to_prevailing_wages': prevailing_wages_county,
    'state_to_poverty_rate': state_to_poverty_rate,
    'county_overrides': inputs_county_overrides,
    'workforce_programs_ipj_map': workforce_programs_ipj_map,
    'discretionary_incentives_groups': discretionary_incentives_groups,
    'sales_apportionment_df': sales_apportionment_df
}

print(json.dumps(project_level_inputs, indent=4))

for state, programs in incentive_programs_by_state.items():
    print('State: {}'.format(state))
    property_tax_rate = prop_taxes_df.loc[state][commercial_or_industrial]
    gross_receipts_tax_rate = tax_foundation_corp_gross_receipts_df.loc[state]['Rate to use']
    if not isinstance(property_tax_rate, float):
        # Take average
        property_tax_rate_values = property_tax_rate.values.tolist()
        property_tax_rate = float(sum(property_tax_rate_values))/len(property_tax_rate_values)
    if not isinstance(gross_receipts_tax_rate, float):
        # Take average
        gross_receipts_tax_rate_values = gross_receipts_tax_rate.values.tolist()
        gross_receipts_tax_rate = float(sum(gross_receipts_tax_rate_values))/len(gross_receipts_tax_rate_values)

    pnl_inputs = dict(
        capex=capex,
        sales=project_level_inputs['Estimated sales based on national data (currently used; estimate or manual input)'],
        costs_of_goods_sold_rate=costs_of_goods_sold,
        salaries_and_wages_adjuster=states_to_share_of_sales_by_sector[state],
        salaries_and_wages_rate=get_salaries_and_wages(inputs_basic['Sector']),
        research_and_development_rate=manual_rd_share_of_sales,
        other_above_the_line_costs_rate=other_above_the_line_costs,
        federal_income_tax_rate=federal_income_tax,
        inflation_rate=inputs_adjustable['Inflation'],
        state_corporate_income_tax_apportionment=states_to_state_corporate_income_tax_apportionment[state],
        state_corporate_income_tax_rate=states_to_state_corporate_income_tax_rates[state],
        state_ui_tax_amount=state_ui_rates_df.loc[state]['Per FTE UI payment ($)'],
        state_local_sales_tax_rate=tax_foundation_corp_sales_tax_df.loc[state]['Combined Rate'],
        gross_receipts_tax_rate=gross_receipts_tax_rate,
        property_tax_rate=property_tax_rate,
        num_jobs=promised_jobs,
        discount_rate=inputs_adjustable['Discount rate'],
        industry_type=industry_type
    )
    pnl = PNL(**pnl_inputs)

    #print(json.dumps(dict(pnl.npv_dicts), indent=4))
    #print('NPV Sales: {}'.format(pnl.npv_sales))
    #print('NPV Net profit: {}'.format(pnl.npv_net_profit))
    #print('Net profitability: {}'.format(pnl.net_profitability))
    all_inputs['pnl'] = pnl
    all_inputs['pnl_inputs'] = pnl_inputs
    for program in programs:
        try:
            incentive = get_incentive_program(
                state,
                program,
                **all_inputs
            )
            eligible = incentive.estimated_eligibility()
            print(f'\tEligibility for {program}: {eligible}')
            if eligible or DEBUG:
                print(f'\t\tEstimated Incentives: {incentive.estimated_incentives()}')
        except ModuleNotFoundError:
            print(f'\tNo python file found for {program}')
        except Exception as e:
            print(f'\tError: {e}')
