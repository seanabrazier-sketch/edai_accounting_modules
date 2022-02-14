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
        ## necessary variable
        machinery = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                      property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        fixture=self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                      property_type=PersonalProperty.FIXTURES)
        construction=self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                      property_type=RealProperty.CONSTRUCTION_MATERIAL)
        sum_val=machinery+fixture+construction
        promised_cap=self.project_level_inputs["Promised capital investment"]
        ratio=(promised_cap-400000000)/promised_cap
        property_tax=self.npv_dicts["Property tax"]
        ##main_tab
        bol_array=[
            "Yes",
            "Yes",
            "Yes" if sum_val>=1000000000 else "No"
        ]
        main_bol="Yes" if bol_array.count("Yes")==3 else "No"
        self.main_bol=main_bol
        main_array=[]
        year=[]
        for i in range(11):
            year.append(i)
            if main_bol=="Yes":
                if i==0:
                    main_array.append(0)
                else:
                    main_array.append(ratio*property_tax[i])
            else:
                main_array.append(0)
        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        return df_dict
