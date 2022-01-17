from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

from util.connecticut_config import  enterprise
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
        #main_tab
        high_level=self.project_level_inputs["High-level category"]
        ## confirm with Sean about the function which is main BOl
        ## row 2357
        main_bol="Yes" if high_level=="Manufacturing" else "No"
        self.main_bol=main_bol
        property_tax=self.npv_dicts["Property tax"]

        if main_bol=="Yes":
            main_array=[i*0.8 for i in property_tax]
        else:
            main_array=[0 for i in range(11)]

        df_dict=defaultdict(list)
        year=[i for i in range(11)]
        df_dict["year"]=year
        main_array[0]=0
        self.sub_array=main_array
        df_dict["value"]=main_array
        return df_dict
