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
        self.county=self.get_county_name()
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

        #necessary variables
        enterprise= [
         'Yes', 'Yes', 'Yes', 'not modeled']
        promised_wage=self.project_level_inputs["Promised wages"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        program=self.all_input["workforce_programs_ipj_map"]["Job training grant"]
        enterprise_array=enterprise[1:-1]
        county_unemploy=self.all_input["county_to_unemployment_rate"]
        state_unemploy=self.all_input["state_to_unemployment_rate"]["Illinois"]
        ## underserved area requirements
        underserved_project_meets_bol="Yes" if enterprise_array.count("Yes")>0 else "No"

        county_pov=None
        if isinstance(self.county,str):
            county_pov=list_of_special_localities["Poverty"][self.county]
        else:
            county_pov=0
        poverty_bol="Yes" if county_pov>=0.2 else "No"
        unemployment_bol=None
        try:
            unemployment_bol="Yes" if county_unemploy[self.county]>=1.2*state_unemploy else "No"
        except:
            unemployment_bol=="No"

        enterprise_zone_bol_array=[underserved_project_meets_bol,poverty_bol,unemployment_bol,"Not modeled"]

        ## share of payroll tax

        ## share of payroll tax
        #bol default for now with poverty --> fix later
        underserved_census_tract="Yes" if county_pov>=0.2 else "No"
        share_of_witholding_tax=0.75 if  underserved_census_tract=="Yes" else 0.5

        ## eligibility
        #default >100 FTEs worldwide
        meet_job_bol="Yes" if promised_jobs>=50 else "No"

        meet_capex_bol="Yes" if self.project_level_inputs["Promised capital investment"]>=2500000 else "No"
        requirement_bol=[
            "Yes",
            "No",
            "Yes",
            meet_job_bol,
            meet_capex_bol




        ]


        ## main_tab
        #check row I1638 wrong condition default main_bol for now.

        main_bol="Yes"
        self.main_bol=main_bol
        share_of_payroll_array=[]
        training_reimburse_array=[]
        main_array=[]
        for i in range(11):
            if main_bol=="Yes":
                if i==0:
                    training_reimburse_array.append(0)
                    share_of_payroll_array.append(0)
                    main_array.append(0)
                else:
                    if i==1:
                        training_reimburse_array.append(promised_jobs*program*0.1)
                    else:
                        training_reimburse_array.append(0)
                    share_of_payroll_array.append(promised_jobs*promised_wage*share_of_witholding_tax*0.0495)
                    main_array.append(training_reimburse_array[-1]+share_of_payroll_array[-1])
        df_dict=defaultdict(list)
        year=[i for i in range(11)]
        df_dict["year"]=year
        df_dict["Share of payroll tax"]=share_of_payroll_array
        df_dict["Training Reibursement"]=training_reimburse_array

        df_dict["value"]=main_array
        return df_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Illinois")
                value = i.replace("Illinois", "IL")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", IL")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
