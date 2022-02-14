from accounting.data_store import *
from accounting.acs_codes import POPULATION_16_YEARS_AND_OVER
import json
from accounting.eligibility_calculator import get_incentive_program
from util.capex import capex_report, IndustryType,RealProperty

from util.personal_income_tax import PersonalIncomeTax
from accounting.sector_shares import get_cost_of_goods_sold, get_other_above_the_line_costs, get_salaries_and_wages
from accounting.states import STATES, abbrev_us_state
from accounting.profit_and_loss import PNL
from accounting.carry_forward import compute_carry_forward_math, IncentiveCategory, IncentiveType, INCENTIVE_TYPE_TO_CATEGORY_MAPPING
from util.npv import excel_npv


DEBUG = True

# TODO pull from DB
federal_income_tax = 0.1323
federal_minimum_wage = 7.25

inputs_county_overrides = {

}


# these are the inputs in the inputs page the user inputs

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
# this variable above will define wheather it is commercial or industrial
# if the input basic is  corporate headquartes or call center then it is commer cial
# else this will define as industrial
# this variblae will be used in the inputs custom capex schedule





industry_type = IndustryType.COMMERCIAL if commercial_or_industrial == 'Commercial' else IndustryType.INDUSTRIAL

# from capex report we can set the variable of industry_type
# industryType is a enum class
# class IndustryType(Enum):
#     INDUSTRIAL='Industrial'
#     DISTRIBUTION_CENTER='Distribution Center'
#     DATA_CENTER='Data Center'
#     COMMERCIAL='Commercial'
#





inputs_capex_schedule = {
    'Total capex': inputs_basic['Promised capital investment'],
    'Automatic capex': commercial_or_industrial,
    'Capex breakout': 'Automatic capex'
}

# Carry forward start
incentive_programs_types = {
    k: IncentiveType.from_str(v) for k, v in incentive_programs_types.items()
}
incentive_programs_categories = {
    k: INCENTIVE_TYPE_TO_CATEGORY_MAPPING[v] for k, v in incentive_programs_types.items()
}

# Sales apportionment calcs
# this is aswell in the user inout
# this is a big data frame in the portion home sales apportionment

census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER] = census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER].astype(float)

#where is this census_acs
# this census_acs_ is in the data_loader.py
# this census_acs_unemp_state_df is in a big table in excel sheet census acs
# check it out





total_population = census_acs_unemp_state_df[POPULATION_16_YEARS_AND_OVER].sum()

# getting the total population from the big data Frame




unemployment_rate_table_code = census_acs_unemp_state_headings_df.loc['Percent Estimate!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force!!Civilian labor force!!Unemployed']['Table code']
# similarly we can get the census_acs_unemp_state_headeings_df from the data_loader
# this census_acs_unemp_state_headings provide all the name of the table
# what this means is we are comparing the index full name attacting out all information from percen ..... and get the code








state_to_unemployment_rate = {
    state: float(census_acs_unemp_state_df.loc[state][unemployment_rate_table_code])/100
    for state in STATES
}

# what this simply means is that we are going to create a json variable where we search for the unemployment rate of different state and we only want the unemployment rate from each state, next we divide that rate from 100




county_to_unemployment_rate = {
    county: float(special_localities_df.loc[county]['Unemployment, 2019']) / 100
    for county in special_localities_df[special_localities_df['Unemployment, 2019']!=''].index.values.tolist()
}


def format_county(county: str) -> str:
    state = county.split(',')[-1].strip()
    state_full = abbrev_us_state[state]
    return county.replace(state, state_full)


county_to_unemployment_rate = {
    format_county(k): v
    for k, v in county_to_unemployment_rate.items()
}

state_to_per_capita_income = {
    state: float(bls_per_capita_income_df.loc[state]['2018'].replace(',','').replace('$', '').strip())
    for state in STATES
}



# this varibale calculate the percapital income from the bls_talbe
# we are goingto replace, and $ and

#
county_to_per_capita_income = {}
# now we want to create county_to_per_capita_income

for county in bls_per_capita_income_df[bls_per_capita_income_df['2018'] != ''].index.values.tolist():

    #first we tell the data frame to getting rid of all the blank values in the frame
    # after that we are going to index that county and make it to a list
    # so now we are looping the the county list

    v = bls_per_capita_income_df.loc[county]['2018']

    # this v is actually the income

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
#we are going to get the input of home state sales apportionment



inputs_home_state_sales_apportionment['Total 16+ population'] = total_population
inputs_home_state_sales_apportionment['Population share'] = sales_apportionment_df.loc[inputs_home_state_sales_apportionment['Home state']]['Share']


inputs_home_state_sales_apportionment['Home state population'] = sales_apportionment_df.loc[inputs_home_state_sales_apportionment['Home state']]['Population 16+ Years']


inputs_home_state_sales_apportionment['Remainder'] =1.0 - inputs_home_state_sales_apportionment['Home state sales share']

# to calculate the manual share of sales
# the formula is going to be
# if state_name =="homestate" then the result is going to be home state sales share
# else the result is going to be the value of non-home state share of population multiply for the remainder
# so how do we calculate the non-home state share
# the non-home state share of population is as foloow
# if state name is == to home state then we just going to put the homstate value because it is equal to the home state sales share
# if not then we use the population of each individual state/ (total population- home state population



## this perhaps is not the formula for state_to_manual_share_of_sales
# in the sales apportionment sheet there are two options for the est home state sales
# we are going to fix this problem by multiplying by the remainder

state_to_manual_share_of_sales = {
    state: inputs_home_state_sales_apportionment['Home state sales share'] if state == inputs_home_state_sales_apportionment['Home state'] \
    else (sales_apportionment_df.loc[state]['Population 16+ Years']/(total_population-inputs_home_state_sales_apportionment['Home state population'])*inputs_home_state_sales_apportionment['Remainder'])
    for state in sales_apportionment_df.index.values.tolist()
}



# this  variable above concludes the information non-home- state share of population




# where is this aproach_to_weights


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


sales_apportionment_df['Property']=sales_apportionment_df['Approach used'].apply(lambda x: approach_to_weights[x][2])



#stop right here
# est home state sales having two options to choose from
# 1 is that it is just going to be = to the population share
# the second ooption is that itis going to be = to the user input manual share of sales
# this manual shares of sales = non home state shares of population*remainder
# we can use ESt.Home State Sales to calculate the tax incidence
# but this perhaps needs to be adjusted to correct formula


sales_apportionment_df['Est. home state sales'] = sales_apportionment_df['Share'].copy()
tax_incidence = []

# the index is the state

for state in sales_apportionment_df.index.tolist():
    r = sales_apportionment_df.loc[state]
    tax_incidence.append(
        # This is perhaps wrong formula and need to adjust

        r['Sales'] * state_to_manual_share_of_sales[state] +
        r['Payroll'] * 1.0 +
        r['Property'] * 1.0)
sales_apportionment_df['Tax incidence (Portion of sales to be taxed)'] = tax_incidence

# Incentives calcs
# we using groupby to calculate the mean, median and predicted of each group in the discretionary sheet
# This would be an easy way to calculated it
# this will be later used to calculate the discretionary informtion in user tab

discretionary_incentives_groups = discretionary_incentives_df[['Program', 'Incentive per job']].groupby('Program')


# Workforce programs
#you just convert this into json variable

#we need to add in predicted IPJ
# discretionary_incentives_groups_median=discretionary_incentives_groups.median()
# discretionary_incentives_groups_average=discretionary_incentives_groups.average()

workforce_programs_ipj_map = {
    program: float(grant_estimates_misc_df.loc[program]['Amount'])
    for program in grant_estimates_misc_df.index.values.tolist()
}


#we will comback to this later
# so we have promised jobs_range
# need to look up where this is going to be used


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


# these inputs is actually from the master incentive models just to find the input in

# just attracting names

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

# at the end all of that information is going to be in the IRS SEctor

# Project level inputs
project_level_inputs = {
    'Attraction or Expansion?': 'Relocation' if inputs_basic['Project Type'] == 'New' else 'Expansion',
    'IRS Sector': inputs_basic['Sector'],
    'Project type': inputs_basic['Project Type'],
    'High-level category': high_level_category,
    'Project category': inputs_basic['Function'],
    'Rollup IRS sector': rollup_irs_sector,
    'Promised jobs': inputs_basic['Promised jobs'],
    'Promised jobs range for state-sector sales estimates': promised_jobs_range,
    'Promised capital investment': inputs_basic['Promised capital investment'],
    'Promised wages': inputs_basic['Promised wages'],
    'P&L Salary state adjuster (on/off)': inputs_adjustable['P&L Salary state adjuster (on/off)'],
    'Wages as share of total compensation (manuf. vs. services)': 0.664 if high_level_category == 'Manufacturing' else 0.707,
    'Census industry earnings name': census_industry_earnings_name,
    'Industry median earnings (Census)': 'Commercial' if inputs_basic['Function'] in ['Corporate headquarters', 'Call center'] else 'Industrial',
    'Calculated estimated sales based on national data': avg_implied_sales,
    'Estimated sales based on national data (currently used; estimate or manual input)': inputs_adjustable['Estimated sales based on national data'],
    'Prevailing wages county': prevailing_wages_county,

    # this missing the based line n/a

    'Estimated sales based on state data (not used)': {
        state: census_susb_state_df.loc[state, promised_jobs_range, rollup_irs_sector]['Avg. implied sales'].astype(float).sum()
        for state in STATES
    },
    'Prevailing wages': prevailing_wages_state,
    #this equipvalent payroll missing the base line argument

    'Equivalent payroll': {
        state: prevailing_wages_state[state] * promised_jobs
        for state in STATES
    },
    # there you go the based

    'Equivalent payroll (BASE)': inputs_basic['Promised wages'] * promised_jobs,
    'Federal minimum wage': federal_minimum_wage,

    #checking up this function

    'State personal income tax': {
        state: PersonalIncomeTax(inputs_basic['Promised wages'], state).tax_rate()
        for state in STATES
    },
    #discount rate given

    'Discount rate': inputs_adjustable['Discount rate'],

    'Inflation (employment cost index)': inputs_adjustable['Inflation'],
}

# Capex
# capex report is a class method
# capex report is in the capex math

capex = capex_report(inputs_capex_schedule['Total capex'])
# print(capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,industry_type=industry_type))
# zone calculation
zone_type_1={
    county:special_localities_df.loc[county]['Zone Type 1']
    for county in special_localities_df.index.values.tolist()
}


zone_type_2={
    county:special_localities_df.loc[county]['Zone Type 2']
    for county in special_localities_df.index.values.tolist()
}

zone_type_3={
    county: special_localities_df.loc[county]['Zone Type 3']
    for county in special_localities_df.index.values.tolist()

}

# county_drop_down_list_input,
# this will be on the front end

county_drop_down_list=["Catron County, NM"]



all_inputs = {
    'capex': capex,
    'project_level_inputs': project_level_inputs,
# State socioeconomic factors
    'state_to_unemployment_rate': state_to_unemployment_rate,
    'state_to_poverty_rate': state_to_poverty_rate,
    'state_to_per_capita_income': state_to_per_capita_income,

    'state_to_prevailing_wages': prevailing_wages_state,
#County socioeconomic factors
    ## missing county poverty, need to bring this up to Sean

    'county_to_prevailing_wages': prevailing_wages_county,
    'county_to_unemployment_rate': county_to_unemployment_rate,
#county_overides is an empty json variable

    'county_overrides': inputs_county_overrides,
    'county_to_per_capita_income': county_to_per_capita_income,

    'workforce_programs_ipj_map': workforce_programs_ipj_map,
    'discretionary_incentives_groups': discretionary_incentives_groups,
    'sales_apportionment_df': sales_apportionment_df,
    'state_to_manual_share_of_sales': state_to_manual_share_of_sales,
    'county_drop_down_list': county_drop_down_list,
# elgibility
    'zone_type_1':zone_type_1,
    'zone_type_2':zone_type_2,
    'zone_type_3':zone_type_3,
## User Input

}

# this is missing in the field. This will be hard coded at beginning but this will be coded to look up for value later on
total_equipment_share_of_sales=0.25
discount_rate = inputs_adjustable['Discount rate']

all_inputs_per_state = {}
for state in incentive_programs_by_state.keys():
    property_tax_rate = prop_taxes_df.loc[state][commercial_or_industrial]
    # this will get the prop_tax rate of each state depends on commercial or industrial

    gross_receipts_tax_rate = tax_foundation_corp_gross_receipts_df.loc[state]['Rate to use']
    # if the property _tax_rate is not float
    # which means that if it returns an array then we want to take average of that array


    if not isinstance(property_tax_rate, float):
        # Take average
        property_tax_rate_values = property_tax_rate.values.tolist()
        property_tax_rate = float(sum(property_tax_rate_values)) / len(property_tax_rate_values)
    if not isinstance(gross_receipts_tax_rate, float):
        # Take average
        # similar to gross_receipts_tax_rate

        gross_receipts_tax_rate_values = gross_receipts_tax_rate.values.tolist()
        gross_receipts_tax_rate = float(sum(gross_receipts_tax_rate_values)) / len(gross_receipts_tax_rate_values)

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
        discount_rate=discount_rate,
        industry_type=industry_type,
        total_equipment_share_of_sales=total_equipment_share_of_sales
    )


    pnl = PNL(**pnl_inputs)
    if state == 'Alabama':
        alabama_npv_dicts = pnl.npv_dicts
    #if state != 'California':
    #    continue
    # print(json.dumps(dict(pnl.npv_dicts), indent=4))
    # print('NPV Sales: {}'.format(pnl.npv_sales))
    # print('NPV Net profit: {}'.format(pnl.npv_net_profit))
    # print('Net profitability: {}'.format(pnl.net_profitability))
    all_inputs['pnl'] = pnl
    all_inputs['pnl_inputs'] = pnl_inputs
    all_inputs_per_state[state] = all_inputs

not_found = []
errors = []
program_outputs = []
state_outputs = []
for state, programs in incentive_programs_by_state.items():
    print('State: {}'.format(state))
    all_inputs = all_inputs_per_state[state].copy()
    all_inputs['all_inputs_per_state'] = all_inputs_per_state
    remaining_tax_liability = None
    for program in programs:
        #if state != 'California' and program != 'Manufacturing and R&D Partial Sales and Use Tax Exemption':
        #    continue
        try:

            incentive = get_incentive_program(
                state,
                program,
                **all_inputs
            )
            eligible = incentive.estimated_eligibility()
            print(f'\tEligibility for {program}: {eligible}')
            estimated_incentives = [0] * 11
            npv = None
            if eligible or DEBUG:
                estimated_incentives = incentive.estimated_incentives()
                if not isinstance(estimated_incentives, list):
                    estimated_incentives = estimated_incentives['value']
                if len(estimated_incentives) != 11:
                    errors.append({
                        'name': f'{state}: {program}',
                        'error': f'Estimated incentives list was not length 11: {len(estimated_incentives)}',
                        'incentives': estimated_incentives
                    })
                    print(f'\t\tEstimated Incentives: {estimated_incentives}')
                    print('\t\tNOT LENGTH 11!!!')
                else:
                    print(f'\t\tEstimated Incentives: {estimated_incentives}')
                    incentive_type = incentive_programs_types[f'{state}_{program}']
                    incentive_category = INCENTIVE_TYPE_TO_CATEGORY_MAPPING[incentive_type]

                    print(f'\t\tIncentive Type: {incentive_type.value}')
                    print(f'\t\tTax liability before: {remaining_tax_liability}')
                    remaining_tax_liability = compute_carry_forward_math(all_inputs['pnl'].npv_dicts,
                                                                         #alabama_npv_dicts,
                                                                         remaining_tax_liability or estimated_incentives,
                                                                         incentive_category)
                    print(f'\t\tTax liability after: {remaining_tax_liability}')
                    try:
                        npv = excel_npv(discount_rate, estimated_incentives)
                    except Exception as e:
                        print(f'\t\tError calculting npv!!')
            program_outputs.append({
                'state': state,
                'program': program,
                'eligibility': eligible,
                #'estimated_incentives': estimated_incentives,
                'estimated_incentives_npv': npv,
                #'remaining_tax_liability': remaining_tax_liability
            })

        except ModuleNotFoundError:
            print(f'\tNo python file found for {program}')
            not_found.append(f'{state}: {program}')
        except Exception as e:
            import traceback
            exc = traceback.format_exc()
            errors.append({
                'name': f'{state}: {program}',
                'error': str(e)
            })
            print(exc)
            print(f'\tError: {e}')
            #raise
    state_outputs.append({
        'state': state,
        #'remaining_tax_liability': remaining_tax_liability,
        'remaining_tax_liability_npv': excel_npv(discount_rate, remaining_tax_liability)
    })

print(f'Not found ({len(not_found)}):')
print(json.dumps(not_found, indent=4))
print(f'Errors ({len(errors)}):')
print(json.dumps(errors, indent=4))

if not os.path.exists('outputs'):
    os.makedirs('outputs' + os.path.sep)

state_output_df = pd.DataFrame(data=state_outputs).set_index(keys=['state'])
state_output_df.to_csv(os.path.join('outputs', 'state_level.csv'))

program_output_df = pd.DataFrame(data=program_outputs)
program_output_df = program_output_df.merge(descriptions_df, how='left', right_index=True, left_on=['state', 'program'])
program_output_df.to_csv(os.path.join('outputs', 'program_level.csv'))

print(program_output_df.head())