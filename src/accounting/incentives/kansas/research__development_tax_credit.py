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

        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts

        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
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
        #necessary variable
        rd=self.npv_dicts["Research & development"]

        #main_tab
        self.main_bol="Yes"

        first_array=[i*0.065 for i in rd][1:4]
        second_array=[]
        for i in range(7):
            array=rd[i+1:i+4]
            sum_val=sum(array)/3

            deduct=rd[i+4]-sum_val

            next_val=deduct*0.065
            second_array.append(next_val)
        for i in second_array:
            first_array.append(i)
        df_dict=defaultdict(list)
        year=[i for i in range(11)]
        main_array=[i*0.25 for i in first_array]
        main_array.insert(0,0)
        df_dict["year"]=year
        df_dict["value"]=main_array
        return  df_dict