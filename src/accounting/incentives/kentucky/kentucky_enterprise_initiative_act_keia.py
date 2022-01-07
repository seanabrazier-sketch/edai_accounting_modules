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
        # self.county=self.get_county_name()
        # self.zone_type_1 = kwargs['zone_type_1']
        # self.zone_type_2 = kwargs['zone_type_2']
        # self.zone_type_3 = kwargs['zone_type_3']
        # self.get_zone = self.get_zone()
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
        year = 7
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
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        state_local_tax=self.pnl_input["state_local_sales_tax_rate"]
        construction_material=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.CONSTRUCTION_MATERIAL)

        #last lsit of array
        array1=[]
        array2=[]
        array3=[]
        main_array=[]
        array4=[]
        array5=[]
        high_level=self.project_level_inputs["High-level category"]
        sector_bol="Yes" if high_level=="R&D Center" else "No"
        year=[]
        anual_exp=self.npv_dicts["Annual capital expenditures option 2"]
        for i in range(11):
            year.append(i)
            if i ==0:
                array1.append(min([20000000,construction_material*state_local_tax]))
                array2.append(machinery*state_local_tax)
                array3.append(0)
                array4.append(0)
                array5.append(0)

                value=array5[-1] if sector_bol=="Yes" else array3[-1]


                main_array.append(array1[-1]+value)
            else:
                array1.append(0)
                array2.append(state_local_tax*anual_exp[i])
                if i==1:
                   val_array=array2[-1]
                   array3.append(val_array)
                else:
                   val_array=array2[1:1+i]

                   array3.append(sum(val_array))

                if i<2:
                    array4.append(0)
                else:
                    array4.append(5000000-array3[i-1] if array3[-1]>5000000 else array3[i-1]-array2[i-1])

                array5.append(max([array4[-1],0]) if array3[-1]>5000000 else array2[-1])

                value = sum(array5[-1],array1[-1]) if sector_bol == "Yes" else sum([array1[-1],array3[-1]])

                main_array.append(value)


        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        self.main_bol="Yes"
        return  df_dict


