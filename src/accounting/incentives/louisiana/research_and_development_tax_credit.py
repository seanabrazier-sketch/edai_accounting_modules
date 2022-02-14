from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

from accounting.incentives.louisiana.industrial_tax_exemption import  IncentiveProgram as sub_class1
from accounting.incentives.louisiana.sales_tax_exemption_on_manufacturing_machinery__equipment import  IncentiveProgram as sub_class2

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sub_class1=sub_class1(**kwargs)
        self.sub_class2=sub_class2(**kwargs)
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
        main_bol="Yes"
        self.main_bol=main_bol

        ## benefit
        promised_job=self.project_level_inputs["Promised jobs"]
        small_business_bol="Yes" if promised_job<50 else "No"
        tax_exemption=[i+j for i,j in zip(self.sub_class1.sub_array,self.sub_class2.sub_array)][0:4]

        array_1=[i*0.06 for i in tax_exemption]

        array_1[0]=0
        rd=self.npv_dicts["Research & development"]
        array2=[]
        array3=[]
        for i in range(1,8):
            rd_array=rd[i:i+3]
            avg_val=sum(rd_array)/3
            fif_val=avg_val*0.5
            eight_val=avg_val*0.8
            current_rd=rd[i+3]
            deduct_val=current_rd-fif_val
            deduct_val2=current_rd-eight_val
            final_val=deduct_val*0.3
            final_val2=deduct_val2*0.3
            array2.append(final_val)
            array3.append(final_val2)

        if small_business_bol=="Yes":
            for i in array2:
                array_1.append(i)
        else:
            for i in array3:
                array_1.append(i)
        year=[i for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=array_1
        return  df_dict






