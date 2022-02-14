from accounting.incentives import *
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']
        self.all_input=kwargs
        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.county=self.get_county_name()
        self.final_return_info=self.final_return()

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
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
        county = self.county
        promised_capital = self.project_level_inputs['Promised capital investment']
        irs_sector = self.project_level_inputs['IRS Sector']
        if isinstance(self.county, str):
            maricopa_pima = 'Yes' if (county == 'Maricopa County' or county == 'Pima County') else 'No'
        else:
            maricopa_pima = 'No'
        ifmaricopa_pima_min_capex = 'Yes' if (maricopa_pima == 'Yes' and promised_capital >= 50000000) else 'No'
        other_min_capex = 'Yes' if maricopa_pima == 'No' else 'No'
        sector_requirements = 'Yes' if irs_sector == 'Data processing, hosting, and related services' else 'No'
        state_local_sale_tax = self.npv_dicts['State/local sales tax']
        tax_rate = self.pnl_input['state_local_sales_tax_rate']
        machinary = self.capex.amount(industry_type=(self.pnl_input['industry_type']),
                                      property_type=(PersonalProperty.MACHINERY_AND_EQUIPMENT))
        df_dict = defaultdict(list)
        for i in range(11):
            df_dict['year'].append(i)
            if sector_requirements == 'No':
                df_dict['value1'].append(0)
                df_dict['value2'].append(0)
                df_dict['value3'].append(0)
            elif i == 0:
                df_dict['value1'].append(state_local_sale_tax[i])
                df_dict['value2'].append(0)
                df_dict['value3'].append(tax_rate * machinary)
            else:
                df_dict['value1'].append(state_local_sale_tax[i])
                df_dict['value2'].append(self.npv_dicts['Gross receipts tax'][i])
                df_dict['value3'].append(tax_rate * machinary)

        def_dict = defaultdict(list)
        def_dict['value'] = df_dict['value1']
        def_dict['year'] = df_dict['year']
        self.main_bol = sector_requirements
        return def_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Arizona")
                value = i.replace("Arizona", "AZ")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", AZ")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county