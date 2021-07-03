import pandas as pd
from util import sales_tax, npv, bls, personal_income_tax, taxed_spending, capex, property_tax
from collections import defaultdict

NPV_YEARS = 10


def model(inputs_basic,
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
    rural_or_city = inputs_miscellaneous['Geography']
    state_wages = bls.StateWages(state)
    state_average_wage = state_wages.average_wage()
    state_average_construction_wage = state_wages.average_construction_wage()

    real_and_personal_property_tax_rate = property_tax.PropertyTax(state=state)\
        .tax_rate(property_tax.PropertyType.Commercial)

    if rural_or_city.lower() == 'city':
        rural_or_city = property_tax.RuralOrCity.City
    else:
        rural_or_city = property_tax.RuralOrCity.Rural

    if capex_category.lower() == 'commercial':
        property_type = property_tax.PropertyType.Commercial
    else:
        property_type = property_tax.PropertyType.Industrial

    local_real_and_personal_property_tax_rate = property_tax.PropertyTax(state=state)\
        .tax_rate(property_type, rural_or_city=rural_or_city)

    construction_labor_cost = capex_report.amount(
        capex.RealProperty.CONSTRUCTION_LABOR,
        capex.IndustryType.from_str(capex_category)
    )
    construction_years = inputs_miscellaneous['Construction years']

    individual_income_tax_rate = personal_income_tax.PersonalIncomeTax(average_salary, state).effective_tax_rate()

    state_sales_tax_rate = sales_tax.SalesTax.state_rate(state)
    local_sales_tax_rate = sales_tax.SalesTax.avg_local_rate(state)

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

    annual_taxable_real_and_personal_property_revenue = taxable_real_and_personal_property * real_and_personal_property_tax_rate
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

    annual_machinery_and_equipment_annual_purchases_revenues = machinery_and_equipment_annual_purchases * state_sales_tax_rate

    direct_employment_steady_state = 0
    construction_employment_steady_state = 0

    local_npv_dict = defaultdict(lambda: [])
    state_npv_dict = defaultdict(lambda: [])

    for i in range(NPV_YEARS):
        if construction_years > 0 and i < construction_years:
            construction_workers = (construction_labor_cost / state_average_construction_wage) / construction_years
            direct_employment_new = 0
            construction_materials = total_construction_materials / construction_years
            annual_construction_materials_revenue = construction_materials * state_sales_tax_rate
        elif ramp_up_years == 0 and i == construction_years:
            construction_workers = 0
            direct_employment_new = total_direct_jobs
            construction_materials = 0
            annual_construction_materials_revenue = 0
        elif ramp_up_years > 0 and i < construction_years + ramp_up_years:
            construction_workers = 0
            direct_employment_new = total_direct_jobs / ramp_up_years
            construction_materials = 0
            annual_construction_materials_revenue = 0
        else:
            construction_workers = 0
            direct_employment_new = 0
            construction_materials = 0
            annual_construction_materials_revenue = 0

        direct_employment_steady_state += direct_employment_new
        annual_payroll = direct_employment_steady_state * average_salary
        annual_personal_income_tax_collected = annual_payroll * individual_income_tax_rate
        expected_taxable_sales = annual_payroll * average_spend_that_is_taxable
        annual_sales_tax_collected = expected_taxable_sales * state_sales_tax_rate
        annual_personal_and_sales_tax_collected_direct = \
            annual_personal_income_tax_collected + annual_sales_tax_collected

        indirect_and_induced_employment = direct_employment_steady_state * additional_employment_multiplier
        annual_payroll_additional_employment = indirect_and_induced_employment * state_average_wage
        annual_personal_income_tax_collected_additional_employment = \
            annual_payroll_additional_employment * individual_income_tax_rate_additional_employment
        expected_taxable_sales_additional_employment = \
            annual_payroll_additional_employment * average_spend_that_is_taxable_additional_employment
        annual_sales_tax_collected_additional_employment = expected_taxable_sales_additional_employment * state_sales_tax_rate
        annual_personal_and_sales_tax_collected_indirect = \
            annual_personal_income_tax_collected_additional_employment + annual_sales_tax_collected_additional_employment

        annual_equipment_and_construction_revenue = (
                annual_taxable_real_and_personal_property_revenue +
                annual_construction_materials_revenue +
                annual_machinery_and_equipment_annual_purchases_revenues
        )

        construction_employment_steady_state += construction_workers
        annual_payroll_construction = construction_employment_steady_state * state_average_construction_wage
        annual_personal_income_tax_collected_construction = \
            annual_payroll_construction * individual_income_tax_rate_construction
        expected_taxable_sales_construction = \
            annual_payroll_construction * average_spend_that_is_taxable_construction
        annual_sales_tax_collected_construction = expected_taxable_sales_construction * state_sales_tax_rate
        annual_personal_and_sales_tax_collected_construction = \
            annual_personal_income_tax_collected_construction + annual_sales_tax_collected_construction

        net_annual_benefits = (
                annual_personal_and_sales_tax_collected_direct +
                annual_personal_and_sales_tax_collected_indirect +
                annual_personal_and_sales_tax_collected_construction +
                annual_equipment_and_construction_revenue
        )

        local_sales_tax_revenues = (
            expected_taxable_sales_construction +
            expected_taxable_sales_additional_employment +
            expected_taxable_sales +
            construction_materials +
            machinery_and_equipment_annual_purchases
        ) * local_sales_tax_rate

        local_annual_taxable_real_and_personal_property_revenues = taxable_real_and_personal_property * local_real_and_personal_property_tax_rate

        state_npv_dict['annual_personal_income_tax_collected'].append(annual_personal_income_tax_collected)
        state_npv_dict['annual_sales_tax_collected'].append(annual_sales_tax_collected)
        state_npv_dict['annual_personal_and_sales_tax_collected_direct'].append(
            annual_personal_and_sales_tax_collected_direct)

        state_npv_dict['annual_personal_income_tax_collected_additional_employment'].append(
            annual_personal_income_tax_collected_additional_employment)
        state_npv_dict['annual_sales_tax_collected_additional_employment'].append(
            annual_sales_tax_collected_additional_employment)
        state_npv_dict['annual_personal_and_sales_tax_collected_indirect'].append(
            annual_personal_and_sales_tax_collected_indirect)

        state_npv_dict['annual_equipment_and_construction_revenue'].append(annual_equipment_and_construction_revenue)

        state_npv_dict['annual_personal_income_tax_collected_construction'].append(
            annual_personal_income_tax_collected_construction)
        state_npv_dict['annual_sales_tax_collected_construction'].append(annual_sales_tax_collected_construction)
        state_npv_dict['annual_personal_and_sales_tax_collected_construction'].append(
            annual_personal_and_sales_tax_collected_construction)

        state_npv_dict['net_annual_benefits'].append(net_annual_benefits)

        local_npv_dict['local_annual_taxable_real_and_personal_property_revenues'].append(local_annual_taxable_real_and_personal_property_revenues)
        local_npv_dict['local_sales_tax_revenues'].append(local_sales_tax_revenues)

    state_npv_dict, state_values_dict, \
    local_npv_dict, local_values_dict = {
        k: npv.npv(discount_rate, v)
        for k, v in state_npv_dict.items()
    }, dict(state_npv_dict), {
        k: npv.npv(discount_rate, v)
        for k, v in local_npv_dict.items()
    }, dict(local_npv_dict)

    #import json
    #print(json.dumps(inputs_miscellaneous, indent=4))

    df = pd.DataFrame(data={
        'Category': [
            'Corporate income taxes',
            'Personal income taxes',
            'Personal income taxes',
            'Personal income taxes',
            'Sales taxes',
            'Sales taxes',
            'Sales taxes',
            'Sales taxes',
            'Property taxes',
            'Sales taxes',
        ],
        'Sub-category': [
            'Corporate income taxes',
            'Direct employment',
            'Indirect employment',
            'Construction labor',
            'Direct employment',
            'Indirect employment',
            'Construction labor',
            'Construction materials (one-time) and annual M&E',
            'Real and personal',
            'Employment, construction materials, and M&E',
        ],
        'State, 10-year NPV': [
            inputs_miscellaneous['10/11 year NPV'],
            state_npv_dict['annual_personal_income_tax_collected'],
            state_npv_dict['annual_personal_income_tax_collected_additional_employment'],
            state_npv_dict['annual_personal_income_tax_collected_construction'],
            state_npv_dict['annual_sales_tax_collected'],
            state_npv_dict['annual_sales_tax_collected_additional_employment'],
            state_npv_dict['annual_sales_tax_collected_construction'],
            state_npv_dict['annual_equipment_and_construction_revenue'],
            None,
            None,
        ],
        'Local, 10-year NPV': [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            local_npv_dict['local_annual_taxable_real_and_personal_property_revenues'],
            local_npv_dict['local_sales_tax_revenues'],
        ]
    }) #.set_index(['Category', 'Sub-category'], drop=True)

    total_benefits_10_year_npv_local = df['Local, 10-year NPV'].dropna().sum()
    total_benefits_10_year_npv_state = df['State, 10-year NPV'].dropna().sum()
    return df, total_benefits_10_year_npv_state, total_benefits_10_year_npv_local