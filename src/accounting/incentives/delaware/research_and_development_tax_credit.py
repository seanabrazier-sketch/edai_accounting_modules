from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
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
        self.rd = self.npv_dicts["Research & development"]
        self.rd_tax = self.rd_tax_credit()



        self.final_return_info=self.final_return()

    def rd_tax_credit(self):
        array1 = [i * 0.06 for i in self.rd][0:4]
        array1[0] = 0
        for i in range(1, 8):
            value = (sum(self.rd[i:i + 3]) / 3) * 0.5
            value = self.rd[i + 3] - value
            value = value * 0.14
            array1.append(value)
        return array1
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

                    if k > year:
                        array_value.append(0)
                    else:

                        array_value.append(final_value[i][k])

                value = excel_npv(self.discount_rate, final_value[i][start_year:year + start_year])
                final_value[i] = array_value
                npv_value.append(value)
        final_value["NPV_Name"] = string_name
        final_value["NPV_Value"] = npv_value

        return final_value
    def final_return(self):
        ##necessary variables
        default_bol="Yes"
        default_rate=0.5
        self.main_bol=default_bol
        df_dict=defaultdict(list)
        main_array=[i*0.5 for i in self.rd_tax]
        main_array[0]=0

        if self.main_bol=="Yes":
            df_dict["value"]=main_array
        else:
            df_dict["value"]=[0 for i in range(11)]
        return df_dict