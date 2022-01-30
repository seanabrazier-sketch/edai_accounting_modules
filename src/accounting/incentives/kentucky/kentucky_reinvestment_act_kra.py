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
        attraction=self.project_level_inputs["Attraction or Expansion?"]
        high_level=self.project_level_inputs["High-level category"]
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)


        bol_array=[
            "Yes" if attraction=="Expansion" else "No",
            "Yes" if high_level=="Manufacturing" else "No",
            "Yes" if machinery>=2500000 else "No"
        ]

        #main
        state_cop=self.npv_dicts["State corporate income tax"]
        main_bol="Yes" if bol_array.count("Yes")==3  else "No"
        if main_bol == "Yes":
            array2=state_cop
        else:
            array2=[0 for i in range(11)]



        array2[0]=0
        sum_val=sum(array2[1:-1])
        value_array3=sum_val*0.0025

        array3=[i*0.0025 if value_array3<50000 else value_array3/10 for i in array2]
        array3[0]=0
        main_array=[i-j for i,j in zip(array2,array3)]
        main_array[0]=0
        df_dict=defaultdict(list)
        year=[i for i in range(11)]
        df_dict["year"]=year
        df_dict["value"]=main_array
        self.main_bol=main_bol
        return df_dict
