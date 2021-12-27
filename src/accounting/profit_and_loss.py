from collections import defaultdict
from util.capex import CapexReport, IndustryType, RealProperty, PersonalProperty
from util.npv import npv


class PNL(object):
    def __init__(self,
                 capex: CapexReport,
                 sales: float,
                 costs_of_goods_sold_rate: float,
                 salaries_and_wages_adjuster: float,
                 salaries_and_wages_rate: float,
                 research_and_development_rate: float,
                 other_above_the_line_costs_rate: float,
                 federal_income_tax_rate: float,
                 state_corporate_income_tax_apportionment: float,
                 state_corporate_income_tax_rate: float,
                 state_ui_tax_amount: float,
                 state_local_sales_tax_rate: float,
                 gross_receipts_tax_rate: float,
                 property_tax_rate: float,
                 inflation_rate: float,
                 discount_rate: float,
                 industry_type: IndustryType,
                 num_jobs: int,
                 n_years: int = 10
                 ):
        npv_dicts = defaultdict(lambda: [])

        construction_material = capex.amount(RealProperty.CONSTRUCTION_MATERIAL, industry_type)
        total_personal_property = (
            capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, industry_type)
            + capex.amount(PersonalProperty.FIXTURES, industry_type)
        )

        total_real_and_personal_property = (
            total_personal_property + construction_material
        )

        total_real_and_personal_property_subject_to_property_tax = (
            capex.amount(RealProperty.LAND, industry_type)
            + total_real_and_personal_property
        )

        # print('Total total_real_and_personal_property: {}'.format(total_real_and_personal_property))
        # print('Total total_personal_property: {}'.format(total_personal_property))
        # print('Total construction_material: {}'.format(construction_material))
        # print('property_tax_rate: {}'.format(property_tax_rate))
        # print('state_local_sales_tax_rate: {}'.format(state_local_sales_tax_rate))
        # print('gross_receipts_tax_rate: {}'.format(gross_receipts_tax_rate))
        # print('state_ui_tax_amount: {}'.format(state_ui_tax_amount))
        # print('state_corporate_income_tax_apportionment: {}'.format(state_corporate_income_tax_apportionment))
        # print('state_corporate_income_tax_rate: {}'.format(state_corporate_income_tax_rate))
        # print('other_above_the_line_costs_rate: {}'.format(other_above_the_line_costs_rate))
        # print('research_and_development_rate: {}'.format(research_and_development_rate))
        # print('salaries_and_wages_rate: {}'.format(salaries_and_wages_rate))
        # print('salaries_and_wages_adjuster: {}'.format(salaries_and_wages_adjuster))
        # print('federal_income_tax_rate: {}'.format(federal_income_tax_rate))

        depreciation_personal_property_years = 5
        depreciation_building_years = 40

        for i in range(n_years+1):
            npv_dicts['Year'].append(i)
            if i == 0:
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
                npv_dicts['State/local sales tax'].append(state_local_sales_tax_rate * total_real_and_personal_property)
                npv_dicts['Gross receipts tax'].append(0.0)
                npv_dicts['Property tax'].append(0.0)
                npv_dicts['Net profit'].append(-npv_dicts['State/local sales tax'][-1])
                npv_dicts['Net profitability'].append(None)
                npv_dicts['Annual capital expenditures'].append(None)
                npv_dicts['R&D tax credit calculations step 0'].append(0.0)
                npv_dicts['R&D tax credit calculations step 1'].append(0.0)
                npv_dicts['R&D tax credit calculations step 2'].append(0.0)
                npv_dicts['R&D tax credit calculations step 3'].append(0.0)
                npv_dicts['R&D tax credit calculations step 4'].append(0.0)
                npv_dicts['Total federal R&D tax credit'].append(0.0)
            else:
                depreciation_building = -construction_material / depreciation_building_years
                depreciation_personal_property = -total_personal_property / depreciation_personal_property_years
                total_property_subject_to_property_tax = -(depreciation_building + depreciation_personal_property)

                if i == 1:
                    npv_dicts['Sales'].append(sales)
                else:
                    npv_dicts['Sales'].append(npv_dicts['Sales'][-1]*(1.0+inflation_rate))

                npv_dicts['Annual capital expenditures'].append(total_property_subject_to_property_tax)
                npv_dicts['Cost of goods sold'].append(npv_dicts['Sales'][-1] * costs_of_goods_sold_rate)
                npv_dicts['Gross profit'].append(npv_dicts['Sales'][-1] - npv_dicts['Cost of goods sold'][-1])
                npv_dicts['State/local sales tax'].append(state_local_sales_tax_rate * total_property_subject_to_property_tax)
                npv_dicts['Salaries and wages'].append(npv_dicts['Sales'][-1] * salaries_and_wages_adjuster * salaries_and_wages_rate)
                npv_dicts['Research & development'].append(npv_dicts['Sales'][-1] * research_and_development_rate)
                npv_dicts['Other above-the-line costs'].append(npv_dicts['Sales'][-1] * other_above_the_line_costs_rate)
                npv_dicts['Income subject to tax'].append(npv_dicts['Gross profit'][-1] - (
                    npv_dicts['Salaries and wages'][-1] + npv_dicts['Research & development'][-1] + npv_dicts['Other above-the-line costs'][-1]
                ))
                npv_dicts['Federal income tax'].append(npv_dicts['Income subject to tax'][-1] * federal_income_tax_rate)
                npv_dicts['State corporate income tax'].append((npv_dicts['Income subject to tax'][-1] * state_corporate_income_tax_apportionment) * state_corporate_income_tax_rate)
                npv_dicts['State UI tax'].append(state_ui_tax_amount * num_jobs)
                npv_dicts['Gross receipts tax'].append(gross_receipts_tax_rate * npv_dicts['Sales'][-1])
                npv_dicts['Property tax'].append(property_tax_rate * total_real_and_personal_property_subject_to_property_tax)
                npv_dicts['Net profit'].append(npv_dicts['Income subject to tax'][-1] - (
                    npv_dicts['Federal income tax'][-1]
                    + npv_dicts['State corporate income tax'][-1]
                    + npv_dicts['State UI tax'][-1]
                    + npv_dicts['State/local sales tax'][-1]
                    + npv_dicts['Gross receipts tax'][-1]
                    + npv_dicts['Property tax'][-1]
                ))
                npv_dicts['Net profitability'].append(npv_dicts['Net profit'][-1] / npv_dicts['Sales'][-1])

                if i <= 3:
                    npv_dicts['R&D tax credit calculations step 0'].append(npv_dicts['Research & development'][-1] * 0.06)
                    npv_dicts['R&D tax credit calculations step 1'].append(0.0)
                    npv_dicts['R&D tax credit calculations step 2'].append(0.0)
                    npv_dicts['R&D tax credit calculations step 3'].append(0.0)
                    npv_dicts['R&D tax credit calculations step 4'].append(0.0)
                else:
                    avg = sum(npv_dicts['Research & development'][-4:-1])/3
                    npv_dicts['R&D tax credit calculations step 0'].append(0.0)
                    npv_dicts['R&D tax credit calculations step 1'].append(avg)
                    npv_dicts['R&D tax credit calculations step 2'].append(avg * 0.5)
                    npv_dicts['R&D tax credit calculations step 3'].append(npv_dicts['Research & development'][-1]-npv_dicts['R&D tax credit calculations step 2'][-1])
                    npv_dicts['R&D tax credit calculations step 4'].append(npv_dicts['R&D tax credit calculations step 3'][-1] * 0.14)
                npv_dicts['Total federal R&D tax credit'].append(npv_dicts['R&D tax credit calculations step 0'][-1]+npv_dicts['R&D tax credit calculations step 4'][-1])

        self.npv_dicts = npv_dicts
        self.npv_sales = npv(discount_rate, amounts=npv_dicts['Sales'])
        self.npv_net_profit = npv(discount_rate, amounts=npv_dicts['Net profit'])
        self.net_profitability = self.npv_net_profit / self.npv_sales
