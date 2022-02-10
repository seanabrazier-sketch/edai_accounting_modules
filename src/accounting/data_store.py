from util import data_loader
from sqlalchemy import create_engine
import pandas as pd, os
from dotenv import load_dotenv, find_dotenv
from util.data_loader import load_cache_csv
load_dotenv()
engine = create_engine(os.environ['DATABASE_URL'])


def load(table, **kwargs):
    return (data_loader.load_from_sql_or_get_from_cache)(engine, table, True, **kwargs)


sales_apportionment_df = load('20210904_Sales appportionment')
sales_apportionment_df.set_index('State', inplace=True, drop=True)
census_acs_unemp_state_df = load('20210904_Census ACS 2018_Unemp state')
census_acs_unemp_state_df = census_acs_unemp_state_df[(census_acs_unemp_state_df.NAME != 'Geographic Area Name')]
census_acs_unemp_state_df.set_index('NAME', inplace=True, drop=True)
census_acs_unemp_state_headings_df = load('20210904_Census ACS 2018_Unemp state_Heading legend')
census_acs_unemp_state_headings_df.set_index('Full name', inplace=True)
census_acs_earn_state_df = load('20210904_Census ACS 2018_Earn State')
census_acs_earn_state_df = census_acs_earn_state_df[(census_acs_earn_state_df.NAME != 'Geographic Area Name')]
census_acs_earn_state_df.set_index('NAME', inplace=True, drop=True)
census_acs_earn_state_headings_df = load('20210904_Census ACS 2018_Earn State_Heading legend')
census_acs_earn_state_headings_df.set_index('Full name', inplace=True)
discretionary_incentives_df = load('20210904_Discretionary Incentives')
discretionary_incentives_df = discretionary_incentives_df[(discretionary_incentives_df['Incentive per job'] != '')]
discretionary_incentives_df['Incentive per job'] = discretionary_incentives_df['Incentive per job'].apply(lambda x: str(x).replace(',', ''))
discretionary_incentives_df['Incentive per job'] = discretionary_incentives_df['Incentive per job'].astype(float)
grant_estimates_misc_df = load('20210904_Grant estimates misc sources 1')
grant_estimates_misc_df.set_index('Grant', inplace=True)
naics_master_crosswalk_df = load('20210904_2017 NAICS master crosswalk')
naics_master_crosswalk_df = naics_master_crosswalk_df[pd.notnull(naics_master_crosswalk_df['Sectors_Census industry earnings'])]
naics_master_crosswalk_df.set_index('Sector_Rollup IRS', inplace=True)
census_industry_crosswalk_df = load('20210904_Census Industry crosswalk')
census_industry_crosswalk_df = census_industry_crosswalk_df[pd.notnull(census_industry_crosswalk_df['Rollup IRS sector'])]
census_industry_crosswalk_df.set_index('Rollup IRS sector', inplace=True)
bls_wages_state_df = load('20210904_BLS - Wages_State')
bls_wages_state_df.set_index('State', inplace=True)
bls_wages_state_df['Annual wages (52 weeks)'] = bls_wages_state_df['Annual wages (52 weeks)'].apply(lambda x: float(x.replace('$', '').replace(',', '')))
bls_wages_county_df = load('20210904_BLS - Wages_County')
bls_wages_county_df.set_index('County', inplace=True)
bls_wages_county_df['Annual wages (52 weeks)'] = bls_wages_county_df['Annual wages (52 weeks)'].apply(lambda x: float(x.replace('$', '').replace(',', '')))
bls_per_capita_income_df = load('20210904_BLS Per capita income')
bls_per_capita_income_df.set_index('County', inplace=True)
census_poverty_state_df = load('20210904_Census Poverty by State', columns=['Name', 'PovPct_All Ages'])
census_poverty_state_df.set_index('Name', inplace=True)
census_susb_state_df = load('20210904_Census SUSB State')
census_susb_state_df['ENTERPRISE EMPLOYMENT SIZE'] = census_susb_state_df['ENTERPRISE EMPLOYMENT SIZE'].apply(lambda x: x.strip().replace('  ', ' '))
census_susb_state_df.set_index(['STATE DESCRIPTION', 'ENTERPRISE EMPLOYMENT SIZE', 'Relevant IRS sector'], inplace=True)
census_susb_national_df = load('20210904_Census SUSB National')
census_susb_national_df['ENTERPRISE EMPLOYMENT SIZE'] = census_susb_national_df['ENTERPRISE EMPLOYMENT SIZE'].apply(lambda x: x.strip().replace('  ', ' '))
indiv_income_taxes_df = load('20210904_Tax Found - Indiv Income Taxes')
indiv_income_taxes_df.set_index(['State', 'Brackets'], inplace=True)
census_acs_industrial_heading = load_cache_csv('20210904_Census ACS 2018_Industry Earni_Heading legend')
census_asc_industrial_earning = load_cache_csv('20210904_Census ACS 2018_Industry Earni')
irs_sector_shares_df = load('20210904_IRS Sector Shares')
irs_sector_shares_df['Sub-category'] = irs_sector_shares_df['Sub-category'].apply(lambda x: x.strip().replace('  ', ' '))
irs_sector_shares_df.set_index('Sub-category', inplace=True)
irs_is_statements_df = load('20210904_IRS I-S Statements')
discretionary_incentives_2 = load('Discretionary Incentives Ca (2)')

def list_of_special_localities():
    list_of_special_localities = load('20210904_ List of Special Localities')
    list_of_special_localities.index = list_of_special_localities['County, State'].tolist()
    return list_of_special_localities


grant_estimates_misc_2_df = load('20210904_Grant estimates misc sources 2')
grant_estimates_misc_2_df.index = grant_estimates_misc_2_df['Program'].tolist()
irs_pl_crosswalks = load('20210904_IRS P&L_Crosswalks')
irs_pl_state_special_sector = load('20210904_IRS P&L State special sectors')
nsf_rd_spending_df = load('20210916_NSF - R&D spending')
nsf_rd_spending_df['IRS corporation categories'] = nsf_rd_spending_df['IRS corporation categories'].apply(lambda x: x.strip().replace('  ', ' '))
nsf_rd_spending_df.set_index('IRS corporation categories', inplace=True)
special_localities_df = load('20210904_ List of Special Localities')
special_localities_df.set_index('County, State', inplace=True)
county_data_compiled_df = load('20210904_County Data Compiled')
county_data_compiled_df.set_index('County, Abbreviation', inplace=True)
special_localities_df = load("20210904_ List of Special Localities")
special_localities_df.set_index("County, State", inplace=True)

county_data_compiled_df = load("20210904_County Data Compiled")
county_data_compiled_df.set_index('County, Abbreviation', inplace=True)

special_localities_df = special_localities_df.merge(county_data_compiled_df, left_index=True, right_index=True, how="inner")

tax_foundation_corp_inc_tax_df = load("20210904_Tax Foundation Corp Inc Tax")
#tax_foundation_corp_inc_tax_df.set_index('State', inplace=True)
tax_foundation_corp_inc_tax_df['Rates'] = tax_foundation_corp_inc_tax_df['Rates'].apply(lambda x: float(x.replace('%', ''))/100 if len(x) > 0 and x != 'None' else 0.0)

tax_foundation_corp_gross_receipts_df = load("20210904_Tax Foundation Gross Receipts")
tax_foundation_corp_gross_receipts_df.set_index('State', inplace=True)
tax_foundation_corp_gross_receipts_df['Rate to use'] = tax_foundation_corp_gross_receipts_df['Rate to use'].apply(lambda x: float(x.replace('%', ''))/100 if len(x) > 0 and x != 'None' else 0.0)

tax_foundation_corp_sales_tax_df = load("20210904_Tax Foundation Sales Tax")
tax_foundation_corp_sales_tax_df['State'] = tax_foundation_corp_sales_tax_df['State'].apply(lambda x: x.split('(')[0].strip())
tax_foundation_corp_sales_tax_df.set_index('State', inplace=True)
tax_foundation_corp_sales_tax_df['Combined Rate'] = tax_foundation_corp_sales_tax_df['Combined Rate'].apply(lambda x: float(x.replace('%', ''))/100 if len(x) > 0 and x != 'None' else 0.0)

prop_taxes_df = load("20210905_Lincoln Inst - Prop Taxes_State output")
prop_taxes_df.set_index('State', inplace=True)
prop_taxes_df['Commercial'] = prop_taxes_df['Commercial tax rate, $1M, avg. urban and rural'].apply(lambda x: float(str(x).replace('%', '')) if len(str(x)) > 0 and x != 'None' else 0.0)
prop_taxes_df['Industrial'] = prop_taxes_df['Industrial tax rate, $1M, avg. urban and rural'].apply(lambda x: float(str(x).replace('%', '')) if len(str(x)) > 0 and x != 'None' else 0.0)

state_ui_rates_df = load("20210904_State UI Rates", columns=['Geography', 'Per FTE UI payment ($)'])
state_ui_rates_df.set_index('Geography', inplace=True)
state_ui_rates_df['Per FTE UI payment ($)'] = state_ui_rates_df['Per FTE UI payment ($)'].apply(lambda x: float(x.replace('$', '').replace(',', '')))
state_specific_sector=load("20210904_State-specific sectors", columns=["AL Property tax", "IRS Returns of active corporations", 'QJ qualifying industries', 'IRS Returns of active corporations'])

state_specific_sectors_df = state_specific_sector.copy()
#state_specific_sectors_df.set_index("Seq. No.", inplace=True)

ne_advantage_sectors_df = load("20210904_NE Advantage Sectors")
engine.dispose()



with open(os.path.join(os.path.dirname(__file__), 'incentive_programs.txt'), 'r',encoding="utf8") as f:
    incentive_programs_list = f.read().strip().splitlines()

with open(os.path.join(os.path.dirname(__file__), 'incentive_programs_types.txt'), 'r',encoding="utf8") as f:
    incentive_programs_types_list = f.read().strip().splitlines()


incentive_programs_types = {
    incentive_programs_list[i]: incentive_programs_types_list[i]
    for i in range(len(incentive_programs_list))
}
incentive_programs_by_state = {}


for p in incentive_programs_list:
    # we are going to split and get the value of of each state
    # then we are going to create a json array to store state the state values as well as program list

    state = p.split('_', 1)[0]
    # get the state name

    program = p.split('_', 1)[1]
    #get the program name

    if state not in incentive_programs_by_state:
        # this means that if state is not in inenctive programs by state
        # so this is a json value
        # which means it will sotre the state as key value

        incentive_programs_by_state[state] = []
        # so now if there is no state in the key value
        # then create a empty array of that state


    # so now we are going to append the program to the array with the json key of state.
    incentive_programs_by_state[state].append(program)

