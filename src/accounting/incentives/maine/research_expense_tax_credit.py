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
from accounting.incentives.maine.employment_tax_increment_financing_program_etif import IncentiveProgram as subclass

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        # self.sub_class=subclass(**kwargs)
        self.capex = kwargs['capex']
        self.all_input=kwargs

        self.pnl_input=kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.default_year=[i for i in range(11)]
        self.rd=self.npv_dicts["Research & development"]
        self.rd_tax = self.rd_tax_credit()
        self.discount_rate = self.project_level_inputs["Discount rate"]
        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
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



    def rd_tax_credit(self):
        array1 = [i * 0.06 for i in self.rd][0:4]
        array1[0] = 0
        deduct=[]
        for i in range(1, 8):
            value = (sum(self.rd[i:i + 3]) / 3) * 0.5
            value = self.rd[i + 3] - value
            deduct.append(value)
            value = value * 0.14
            array1.append(value)
        self.deduct=deduct
        return array1

    def final_return(self):
        rd=self.npv_dicts["Research & development"]
        array1=[i*0.05 for i in rd][0:4]
        array1[0]=0
        ## mising tax credit tab
        ## line 143
        ## set default for now Q149
        ## look for formula at row Q2495
        # list_ray=[105547813,108503151,111541240,114664394,117874997,121175497,124568411]

        array2=[i*0.05 for i in self.deduct]
        ## mising else statement in thsi formula
        ## look for row Q2496 for more information
        array3=[25000+(i-25000)*0.75 if i>25000 else 0 for i in array2]

        self.main_bol="Yes"
        if self.main_bol=="Yes":
            for i in array3:
                array1.append(i)
            main_array=array1
        else:
            main_array=[0 for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict