from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']
        self.all_input=kwargs
        self.county=self.get_county_name()

        self.get_zone = self.get_zone()
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
        year = 1
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
        promised_wage=self.project_level_inputs["Promised wages"]
        #enterprise Zone
        # Project meets
        prevailing_wages=self.project_level_inputs['Prevailing wages']["Colorado"]

        per_capital_income = self.all_input["state_to_per_capita_income"]["Colorado"]
        county_capital_income = self.all_input["county_to_per_capita_income"][self.county] if len(
            self.county) > 0 else per_capital_income
        per_capital_less75 = "Yes" if county_capital_income < 0.75 * per_capital_income else "No"

        county_unemployment = self.all_input["county_to_unemployment_rate"][self.county] if len(self.county) > 0 else 0
        state_unempoyment = self.all_input["state_to_unemployment_rate"]["Colorado"]
        ## this is an error and we need to raise this to Sean
        ## in the excel sheet this should return no instead of Yes

        unem_greater25 = "Yes" if county_unemployment > state_unempoyment * 1.25 else "No"
        population_growth = "Not model"

        projects_meets_main_bol = "Yes" if (unem_greater25 == "Yes" or population_growth == "Yes" or per_capital_less75 == "Yes") else "No"





        #g11 promised jobs
        promised_jobs=self.project_level_inputs["Promised jobs"]

        #g13 promised capital investment'

        promised_capital_investment=self.project_level_inputs["Promised capital investment"]
        #requirement

        minimum_capex="Yes" if promised_capital_investment>=promised_jobs*100000 else "No"

        boolean_array=[minimum_capex,"Yes","Yes"]
        count_yes=boolean_array.count("Yes")
        model_main_bool="Yes" if count_yes==3 else "No"

        ## create df to use value
        annual_county_wage=[1,1.1,1.2,1.3,1.4]
        non_ez=[2500,2500,3500,3500,5000]
        eligible=["Yes" if (promised_wage>=(annual_county_wage[i]*prevailing_wages)) else "No" for i in range(len(annual_county_wage))]

        non_ez_yes=[]
        for i in range(len(non_ez)):
            if eligible[i]=="Yes":
                non_ez_yes.append(non_ez[i])



        to_use=max(non_ez_yes)



        value_array=[0,to_use*promised_jobs if model_main_bool=="Yes" else 0]

        df_dict=defaultdict(list)
        year=[0,1]
        df_dict["year"]=year
        df_dict["value"]=value_array
        self.main_bol=model_main_bool

        return df_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Colorado")
                value = i.replace("Colorado", "CO")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", CO")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

    def get_zone(self):

        try:
            zone_type_1 = list_of_special_localities["Zone Type 1"]
            self.zone_type_1 = zone_type_1[self.county]
            if len(self.zone_type_1) == 0:
                self.zone_type_1 = "-"
        except:
            self.zone_type_1 = "-"
        try:
            zone_type_2 = list_of_special_localities["Zone Type 2"]
            self.zone_type_2 = zone_type_2[self.county]
            if len(self.zone_type_2) == 0:
                self.zone_type_2 = "-"
        except:
            self.zone_type_2 = "-"
        try:
            zone_type_3 = list_of_special_localities["Zone Type 3"]
            self.zone_type_3 = zone_type_3[self.county]
            if len(self.zone_type_3) == 0:
                self.zone_type_3 = "-"

        except:
            self.zone_type_3 = "-"
