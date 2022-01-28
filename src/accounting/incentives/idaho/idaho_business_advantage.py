from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']
        self.all_input=kwargs
        # self.county=self.get_county_name()
        # self.zone_type_1 = kwargs['zone_type_1']
        # self.zone_type_2 = kwargs['zone_type_2']
        # self.zone_type_3 = kwargs['zone_type_3']
        # self.get_zone = self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts

        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year = 10
        final_value = self.final_return_info
        npv_value = []
        string_name = []
        start_year = 0

        for i in self.final_return_info:
            if i != "year" and i != "Year":
                array_value = []

                string = "npv_{}".format(i)
                string_name.append(string)
                for k in range(11):
                    if k < start_year:
                        array_value.append("Base")
                        continue

                    if k > year + start_year:
                        array_value.append(0)
                    else:

                        array_value.append(final_value[i][k])

                value = excel_npv(self.discount_rate, final_value[i][start_year:year + 1 + start_year])
                final_value[i] = array_value
                npv_value.append(value)
        final_value["NPV_Name"] = string_name
        final_value["NPV_Value"] = npv_value

        return final_value

    def final_return(self):
        state_ui_tax = self.npv_dicts['State UI tax']
        promised_job = self.project_level_inputs['Promised jobs']
        promised_wage = self.project_level_inputs['Promised wages']
        promised_capital = self.project_level_inputs['Promised capital investment']
        property_tax = self.npv_dicts['Property tax'][1:]
        state_local_sale_tax = self.pnl_input['state_local_sales_tax_rate']
        real_construction_material = self.capex.amount(property_type=(RealProperty.CONSTRUCTION_MATERIAL), industry_type=(self.pnl_input['industry_type']))
        fixture = self.capex.amount(property_type=(PersonalProperty.FIXTURES), industry_type=(self.pnl_input['industry_type']))
        machinery = self.capex.amount(property_type=(PersonalProperty.MACHINERY_AND_EQUIPMENT), industry_type=(self.pnl_input['industry_type']))
        sum_prop = real_construction_material + fixture + machinery
        requirement_bol_array = [
         'Yes' if promised_job >= 10 else 'No',
         'Yes' if promised_wage >= 40000 else 'No',
         'Yes' if promised_capital >= 500000 else 'No']
        default_employer_bol = 'No'
        default_employer_array = None
        if default_employer_bol == 'Yes':
            default_employer_array = property_tax
        else:
            default_employer_array = [0 for i in range(11)]
        default_employer_array[0] = 0
        sales_and_use_tax_array = [
         0.25 * state_local_sale_tax * sum_prop]
        for i in range(10):
            sales_and_use_tax_array.append(0)

        new_jobs_tax_credit_default_bol = 'Yes'
        value_lookup = promised_wage / 2080
        array_lookup = [24.04, 28.86, 36.07, 43.28]
        array_return = [1500, 2000, 2500, 3000]
        new_jobs_tax_credit_val = v_lookup_2(value_lookup, array_lookup, array_return)
        new_jobs_tax_credit_array = [0]
        new_jobs_tax_credit_array.append(promised_job * new_jobs_tax_credit_val if new_jobs_tax_credit_default_bol == 'Yes' else 0)
        for i in range(9):
            new_jobs_tax_credit_array.append(0)

        real_property_improvement_default_bol = 'Yes'
        real_property_improvement_array = [0]
        real_property_improvement_array.append(real_construction_material * 0.025 if real_property_improvement_default_bol == 'Yes' else 0)
        for i in range(9):
            real_property_improvement_array.append(0)

        real_property_improvement_array_2 = [
         0]
        for i in range(10):
            real_property_improvement_array_2.append(real_property_improvement_array[1] / 14 if real_property_improvement_array[1] > 125000 else real_property_improvement_array[1])

        investment_tax_credit_default_bol = 'Yes'
        against_corporate = [0]
        against_corporate.append(machinery * 0.0375 if investment_tax_credit_default_bol == 'Yes' else 0)
        for i in range(9):
            against_corporate.append(0)

        ceiling_array = [min([i, 0.625 * j, 7500000]) if investment_tax_credit_default_bol == 'Yes' else 'No' for i, j in zip(against_corporate, state_ui_tax)]
        ceiling_array[0] = 0
        value1 = against_corporate[1]
        value2 = ceiling_array[1]
        investment_tax_credit_main_array = [i / 14 if i > j else i for i, j in zip(against_corporate, ceiling_array)]
        investment_tax_credit_main_array = investment_tax_credit_main_array[0:1]
        for i in range(10):
            investment_tax_credit_main_array.append(0 if value1 < value2 else value1 / 14)

        main_bol = 'Yes' if requirement_bol_array.count('Yes') == 3 else 'No'
        main_array = [i + j + k + l + n if main_bol == 'Yes' else 0 for i, j, k, l, n in zip(default_employer_array, sales_and_use_tax_array, new_jobs_tax_credit_array, real_property_improvement_array_2, investment_tax_credit_main_array)]
        year = [i for i in range(11)]
        df_dict = defaultdict(list)
        df_dict['year'] = year
        df_dict['sales and tax rebate of 25%'] = sales_and_use_tax_array
        df_dict['Small employer growth incentive'] = default_employer_array
        self.main_bol = main_bol
        df_dict['benefit'] = investment_tax_credit_main_array
        df_dict['value'] = main_array
        return df_dict
