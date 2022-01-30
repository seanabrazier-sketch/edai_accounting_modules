import os.path

from accounting.incentives import *
import numpy
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
        # self.county=self.get_county_name()
        # self.zone_type_1 = kwargs['zone_type_1']
        # self.zone_type_2 = kwargs['zone_type_2']
        # self.zone_type_3 = kwargs['zone_type_3']
        # self.get_zone = self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts

        self.final_return_info=self.final_return()

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]

        year = 11
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
        df_dict = defaultdict(list)
        sales = self.npv_dicts['Sales']
        default_array = [
         'Yes', 'Yes', 'Yes', 'not modeled']
        # self.enterprise = default_array
        # path = connecticut_config.__file__
        # file = open(path, 'w')
        # file.write('enterprise={}'.format(self.enterprise))
        # file.close()
        research_and_development = self.npv_dicts['Research & development']
        year = 10
        return_lookup = ['<$50M', '$50M-$100M', '$101M-$200M', '>$200M']
        for i in range(year + 1):
            df_dict['year'].append(i)
            if i == 0:
                df_dict['value'].append(0)
                df_dict['value_choose'].append(0)
            else:
                df_dict['rd_value1'].append(0.01 * research_and_development[i])
                df_dict['rd_value2'].append(500000 + 0.02 * (50000000 - research_and_development[i]))
                df_dict['rd_value3'].append(1500000 + 0.04 * (100000000 - research_and_development[i]))
                df_dict['rd_value4'].append(5500000 + 0.06 * (200000000 - research_and_development[i]))
                df_dict['rd_lookup'].append(self.rd_lookupup(research_and_development[i]))
                value_stack = [df_dict['rd_value1'][(-1)], df_dict['rd_value2'][(-1)], df_dict['rd_value3'][(-1)], df_dict['rd_value4'][(-1)]]
                index = return_lookup.index(df_dict['rd_lookup'][(-1)])
                df_dict['value_choose'].append(value_stack[index])

        for i in range(year + 1):
            if i == 0:
                df_dict['eligibility_value1'].append(0)
                df_dict['eligibility_value2'].append(0)
                df_dict['eligibility_value3'].append(0)
            else:
                df_dict['eligibility_value1'].append('Yes' if sales[i] < 100000000 else 'No')
                df_dict['eligibility_value2'].append(0.06 * research_and_development[i] if df_dict['eligibility_value1'][(-1)] == 'Yes' else 'n/a')

        incremental_array = []
        for i in range(11):
            if i < 2:
                incremental_array.append(0)
            else:
                incremental_array.append((research_and_development[i] - research_and_development[(i - 1)]) * 0.2)

        self.main_bol = 'Yes'
        value_dict = defaultdict(list)
        main_array = [i + k for i, k in zip(df_dict['value_choose'], incremental_array)]
        value_dict["Incremental R&D credit"]=incremental_array
        value_dict["Non-incremental R&D credit"]=df_dict["value_choose"]
        if self.main_bol == 'Yes':
            value_dict['value'] = main_array
        else:
            value_dict['value'] = [0 for i in range(11)]
        value_dict['year'] = [i for i in range(11)]

        return value_dict


    def rd_lookupup(self,value):

        array_lookup = [0, 50000001, 100000001, 200000001]
        return_lookup = ["<$50M", "$50M-$100M", "$101M-$200M", ">$200M"]
        try:
            variance=[1000000/(value-i) for i in array_lookup]
            sort_val=sorted(variance,reverse=True)
            max_val=max(sort_val)
            choose_max_index=variance.index(max_val)
            return_val=return_lookup[choose_max_index]
            return return_val
        except:
            variance=[value-i for i in array_lookup]
            index_val=variance.index(0)
            return return_lookup[index_val]






