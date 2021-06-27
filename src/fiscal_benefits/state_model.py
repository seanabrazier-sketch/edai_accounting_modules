import pandas as pd
from util import sales_tax, npv, bls, personal_income_tax, taxed_spending, capex, property_tax
from collections import defaultdict

NPV_YEARS = 10


def state_model(inputs_basic,
                inputs_adjustable,
                inputs_miscellaneous):

    discount_rate = inputs_adjustable['Discount rate']
    building_depreciation_years = 40
    machinery_and_equipment_depreciation_years = 5

    capital_investment = inputs_basic['Promised capital investment']
    total_direct_jobs = inputs_basic['Promised jobs']
    average_salary = inputs_basic['Promised wages']
    ramp_up_years = inputs_miscellaneous['Employment rampup']
    state = inputs_miscellaneous['State focus']
    additional_employment_multiplier = 5.143
    capex_report = capex.capex_report(capital_investment)
    capex_category = inputs_miscellaneous['Capital investment category']

    state_wages = bls.StateWages(state)
    state_average_wage = state_wages.average_wage()
    state_average_construction_wage = state_wages.average_construction_wage()

    real_and_personal_property_tax_rate = property_tax.PropertyTax(state=state)\
        .tax_rate(property_tax.PropertyType.Commercial)

    construction_labor_cost = capex_report.amount(
        capex.RealProperty.CONSTRUCTION_LABOR,
        capex.IndustryType.from_str(capex_category)
    )
    construction_years = inputs_miscellaneous['Construction years']

    individual_income_tax_rate = personal_income_tax.PersonalIncomeTax(average_salary, state).effective_tax_rate()
    sales_tax_rate = sales_tax.SalesTax.combined_rate(state)
    average_spend_that_is_taxable = taxed_spending.estimated_taxable_as_share_of_income(average_salary)

    individual_income_tax_rate_additional_employment = personal_income_tax.PersonalIncomeTax(state_average_wage,
                                                                                             state).effective_tax_rate()
    average_spend_that_is_taxable_additional_employment = taxed_spending.estimated_taxable_as_share_of_income(
        state_average_wage)

    individual_income_tax_rate_construction = personal_income_tax.PersonalIncomeTax(state_average_construction_wage,
                                                                                    state).effective_tax_rate()
    average_spend_that_is_taxable_construction = taxed_spending.estimated_taxable_as_share_of_income(
        state_average_construction_wage)

    total_construction_materials = capex_report.amount(
        capex.RealProperty.CONSTRUCTION_MATERIAL,
        capex.IndustryType.from_str(capex_category)
    )

    taxable_real_and_personal_property = sum([
        capex_report.amount(
            property_type,
            capex.IndustryType.from_str(capex_category)
        ) for property_type in [
            capex.PersonalProperty.MACHINERY_AND_EQUIPMENT,
            capex.PersonalProperty.FIXTURES,
            capex.RealProperty.CONSTRUCTION_MATERIAL,
            capex.RealProperty.LAND
        ]
    ])

    annual_taxable_real_and_personal_property = taxable_real_and_personal_property * real_and_personal_property_tax_rate
    machinery_and_equipment_annual_purchases = (
                                                       capex_report.amount(
                                                           capex.PersonalProperty.MACHINERY_AND_EQUIPMENT,
                                                           capex.IndustryType.from_str(capex_category)
                                                       ) / machinery_and_equipment_depreciation_years
                                               ) + (
                                                       capex_report.amount(
                                                           capex.RealProperty.CONSTRUCTION_MATERIAL,
                                                           capex.IndustryType.from_str(capex_category)
                                                       ) / building_depreciation_years
                                               )

    annual_machinery_and_equipment_annual_purchases_revenues = machinery_and_equipment_annual_purchases * sales_tax_rate

    direct_employment_steady_state = 0
    construction_employment_steady_state = 0

    npv_dict = defaultdict(lambda: [])

    for i in range(NPV_YEARS):
        if construction_years > 0 and i < construction_years:
            construction_workers = (construction_labor_cost / state_average_construction_wage) / construction_years
            direct_employment_new = 0
            construction_materials = total_construction_materials / construction_years
            annual_construction_materials_revenue = construction_materials * sales_tax_rate
        elif ramp_up_years == 0 and i == construction_years:
            construction_workers = 0
            direct_employment_new = total_direct_jobs
            annual_construction_materials_revenue = 0
        elif ramp_up_years > 0 and i < construction_years + ramp_up_years:
            construction_workers = 0
            direct_employment_new = total_direct_jobs / ramp_up_years
            annual_construction_materials_revenue = 0
        else:
            construction_workers = 0
            direct_employment_new = 0
            annual_construction_materials_revenue = 0

        direct_employment_steady_state += direct_employment_new
        annual_payroll = direct_employment_steady_state * average_salary
        annual_personal_income_tax_collected = annual_payroll * individual_income_tax_rate
        expected_taxable_sales = annual_payroll * average_spend_that_is_taxable
        annual_sales_tax_collected = expected_taxable_sales * sales_tax_rate
        annual_personal_and_sales_tax_collected_direct = \
            annual_personal_income_tax_collected + annual_sales_tax_collected

        indirect_and_induced_employment = direct_employment_steady_state * additional_employment_multiplier
        annual_payroll_additional_employment = indirect_and_induced_employment * state_average_wage
        annual_personal_income_tax_collected_additional_employment = \
            annual_payroll_additional_employment * individual_income_tax_rate_additional_employment
        expected_taxable_sales_additional_employment = \
            annual_payroll_additional_employment * average_spend_that_is_taxable_additional_employment
        annual_sales_tax_collected_additional_employment = expected_taxable_sales_additional_employment * sales_tax_rate
        annual_personal_and_sales_tax_collected_indirect = \
            annual_personal_income_tax_collected_additional_employment + annual_sales_tax_collected_additional_employment

        annual_equipment_and_construction_revenue = (
                annual_taxable_real_and_personal_property +
                annual_construction_materials_revenue +
                annual_machinery_and_equipment_annual_purchases_revenues
        )

        construction_employment_steady_state += construction_workers
        annual_payroll_construction = construction_employment_steady_state * state_average_construction_wage
        annual_personal_income_tax_collected_construction = \
            annual_payroll_construction * individual_income_tax_rate_construction
        expected_taxable_sales_construction = \
            annual_payroll_construction * average_spend_that_is_taxable_construction
        annual_sales_tax_collected_construction = expected_taxable_sales_construction * sales_tax_rate
        annual_personal_and_sales_tax_collected_construction = \
            annual_personal_income_tax_collected_construction + annual_sales_tax_collected_construction

        net_annual_benefits = (
                annual_personal_and_sales_tax_collected_direct +
                annual_personal_and_sales_tax_collected_indirect +
                annual_personal_and_sales_tax_collected_construction +
                annual_equipment_and_construction_revenue
        )

        npv_dict['annual_personal_income_tax_collected'].append(annual_personal_income_tax_collected)
        npv_dict['annual_sales_tax_collected'].append(annual_sales_tax_collected)
        npv_dict['annual_personal_and_sales_tax_collected_direct'].append(
            annual_personal_and_sales_tax_collected_direct)

        npv_dict['annual_personal_income_tax_collected_additional_employment'].append(
            annual_personal_income_tax_collected_additional_employment)
        npv_dict['annual_sales_tax_collected_additional_employment'].append(
            annual_sales_tax_collected_additional_employment)
        npv_dict['annual_personal_and_sales_tax_collected_indirect'].append(
            annual_personal_and_sales_tax_collected_indirect)

        npv_dict['annual_equipment_and_construction_revenue'].append(annual_equipment_and_construction_revenue)

        npv_dict['annual_personal_income_tax_collected_construction'].append(
            annual_personal_income_tax_collected_construction)
        npv_dict['annual_sales_tax_collected_construction'].append(annual_sales_tax_collected_construction)
        npv_dict['annual_personal_and_sales_tax_collected_construction'].append(
            annual_personal_and_sales_tax_collected_construction)

        npv_dict['net_annual_benefits'].append(net_annual_benefits)

    return {
        k: npv.npv(discount_rate, v)
        for k, v in npv_dict.items()
    }, dict(npv_dict)
