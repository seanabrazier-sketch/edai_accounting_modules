# note: This profit and loss sheet is in master incentives model excel sheet.


from collections import defaultdict
from util.capex import CapexReport, IndustryType, RealProperty, PersonalProperty
from util.npv import npv
## PNL inherit the CapexReport
npv_dicts = defaultdict(lambda: [])




## testing phase



class PNL(object):
    def __init__(self,
                 capex: CapexReport,
                 sales: float,
                 costs_of_goods_sold_rate: float,
                 #salaries and wages adjuster is used to calcalculate salaries and wages
                 # excel sheet formula for salaries and wages adjuster
                 #this will be a lookup variable from differnt tab

                 salaries_and_wages_adjuster: float,
                 salaries_and_wages_rate: float,
                 research_and_development_rate: float,
                 other_above_the_line_costs_rate: float,
                 federal_income_tax_rate: float,
                 state_corporate_income_tax_apportionment: float,
                 state_corporate_income_tax_rate: float,
                 state_ui_tax_amount: float,
                 # this rate is also a lookup from other tab
                 # check this out in the model incentives tab

                 state_local_sales_tax_rate: float,
                 gross_receipts_tax_rate: float,
                 property_tax_rate: float,
                 inflation_rate: float,
                 discount_rate: float,
                 industry_type: IndustryType,
                 # num_jobs is promised jobs.

                 num_jobs: int,
                 #total eqiment share of sales, this variable will be lookup in capex sheet

                 total_equipment_share_of_sales:float,
                 n_years: int = 10


                 ):
        npv_dicts=defaultdict(lambda:[])
        construction_material=capex.amount(RealProperty.CONSTRUCTION_MATERIAL,industry_type)
        real_property_land=capex.amount(RealProperty.LAND,industry_type)
        # construction_material
        # we call in the class capex.amount which gets the value of Construction_material based on what Industry_type


        total_personal_property=(capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT,industry_type)+capex.amount(PersonalProperty.FIXTURES,industry_type))
        # next is the total_personal_property
        # this will return the PersonalProperty of machineary and equpmaent based on industry_type+ and the Fixtures of that industry_type
        total_real_property=construction_material+real_property_land
        total_real_and_personal_property_subject_to_property_tax=(total_personal_property+total_real_property)

        # this total is the sum of construction material on the real property and total_personal proeprt
        total_real_and_personal_property_subject_to_sales_tax = total_personal_property + construction_material
        print(total_real_and_personal_property_subject_to_property_tax)
        depreciation_personal_property_years=5
        # depreciation is set to 5
        depreciation_building_years=40
        # building depreciation is set to 40
        for i in range(n_years+1):
            # n_year is set to default=10
            # this loop will loop through 0-10
            npv_dicts['Year'].append(i)
            #we append the year from 0-10 to the Npv_dictionary
            if i==0:
                npv_dicts['Sales'].append(0.0)
                npv_dicts['Cost of goods sold'].append(0.0)
                npv_dicts['Gross profit'].append(0.0)
                npv_dicts['Salaries and wages'].append(0.0)
                npv_dicts['Research & development'].append(0.0)
                npv_dicts['Other above-the-line costs'].append(0.0)
                npv_dicts['Income subject to tax'].append(0.0)
                npv_dicts['Federal income tax'].append(0.0)
                npv_dicts['State corporate income tax'].append(0.0)
                npv_dicts['State UI tax'].append(0.0)
                npv_dicts['State/local sales tax'].append(state_local_sales_tax_rate * total_real_and_personal_property_subject_to_sales_tax)
                npv_dicts['Gross receipts tax'].append(0.0)
                npv_dicts['Property tax'].append(0.0)
                npv_dicts['Net profit'].append(-npv_dicts['State/local sales tax'][-1])
                npv_dicts['Net profitability'].append(None)
                npv_dicts['Annual capital expenditures option 1'].append(None)
                npv_dicts['Annual capital expenditures option 2'].append(None)




            else:

                depreciation_building=-construction_material/depreciation_building_years
                depreciation_personal_property=-total_personal_property/depreciation_personal_property_years


                # total_property_subject_to_property_tax=-(depreciation_building+depreciation_personal_property)
                ## This does not follow the excel formula
                # this should be annual capital expenditures



                if i==1:
                    npv_dicts['Sales'].append(sales)
                else:
                    # if sales is the year 0 then append 0
                    # if sales is the first year then we just append the sales value
                    # if sales actually above 1 year then we
                    #get the sales value from the previous year, then we are going to multiply that with 1+ inflation rate

                    npv_dicts['Sales'].append(npv_dicts['Sales'][-1]*(1+inflation_rate))
                npv_dicts['Annual capital expenditures option 1'].append(npv_dicts['Sales'][-1]*total_equipment_share_of_sales)
                npv_dicts['Annual capital expenditures option 2'].append(-(depreciation_building + depreciation_personal_property))
                # we can use annual capital expenditures option 2 as anual capital expenditures

                npv_dicts['Annual capital expenditures'].append(npv_dicts['Annual capital expenditures option 2'][-1])



                npv_dicts['Cost of goods sold'].append(npv_dicts['Sales'][-1]*costs_of_goods_sold_rate)
                npv_dicts['Gross profit'].append(npv_dicts['Sales'][-1]-npv_dicts['Cost of goods sold'][-1])
                npv_dicts['State/local sales tax'].append(state_local_sales_tax_rate)

                npv_dicts['Salaries and wages'].append(npv_dicts['Sales'][-1]*salaries_and_wages_adjuster*salaries_and_wages_rate)
                npv_dicts['Research & development'].append(npv_dicts['Sales'][-1]*research_and_development_rate)
                npv_dicts['Other above-the-line costs'].append(npv_dicts['Sales'][-1]*other_above_the_line_costs_rate)
                npv_dicts['Income subject to tax'].append(npv_dicts['Gross profit'][-1]-(npv_dicts['Salaries and wages'][-1]+npv_dicts['Research & development'][-1]+npv_dicts['Other above-the-line costs'][-1]))
                npv_dicts['Federal income tax'].append(npv_dicts['Income subject to tax'][-1]*federal_income_tax_rate)
                npv_dicts['State corporate income tax'].append((npv_dicts['Income subject to tax'][-1]*state_corporate_income_tax_rate*state_corporate_income_tax_apportionment))

                npv_dicts['State UI tax'].append(state_ui_tax_amount*num_jobs)
                npv_dicts['Gross receipts tax'].append(gross_receipts_tax_rate*npv_dicts['Sales'][-1])
                npv_dicts['Property tax'].append(property_tax_rate*total_real_and_personal_property_subject_to_property_tax)
                npv_dicts['Net profit'].append(npv_dicts['Income subject to tax'][-1] - (
                        npv_dicts['Federal income tax'][-1]
                        + npv_dicts['State corporate income tax'][-1]
                        + npv_dicts['State UI tax'][-1]
                        + npv_dicts['State/local sales tax'][-1]
                        + npv_dicts['Gross receipts tax'][-1]
                        + npv_dicts['Property tax'][-1]
                ))
                npv_dicts['Net profitability'].append(npv_dicts['Net profit'][-1] / npv_dicts['Sales'][-1])

            self.npv_dicts=npv_dicts
            self.npv_sales = npv(discount_rate, amounts=npv_dicts['Sales'])
            self.npv_net_profit = npv(discount_rate, amounts=npv_dicts['Net profit'])
            self.net_profitability = self.npv_net_profit / self.npv_sales
