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

        self.get_zone = self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts

        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False
    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year = 6
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
        ## necessary variables
        promised_jos=self.project_level_inputs["Promised jobs"]
        promised_wage=self.project_level_inputs["Promised wages"]
        county_prevailing_wages=None
        state_prevailing_wages=self.project_level_inputs["Prevailing wages"]["Georgia"]
        if isinstance(self.county,str):
            county_prevailing_wages=self.project_level_inputs["Prevailing wages count"][self.county]
        else:

            county_prevailing_wages=state_prevailing_wages


        ## meet frame
        QJTC_credit=[2500,3000,4000,4500,5000]
        rate_array=[1.1,1.2,1.5,1.75,2]
        meets_array=[
            "Yes" if promised_wage>=i*county_prevailing_wages else "No" for i in rate_array]

        ## requirement
        requirement_wages_bol="Yes" if promised_wage>=county_prevailing_wages*1.1 else "No"
                    ## zone type 2 is going to be a number

        tier_array=["Tier 1","Tier 2","Tier 3","Tier 4"]
        geographic_teir=None
        try:
            geographic_teir=tier_array[self.zone_type_2-1]
        except:
            geographic_teir="Tier 3"
        self.geographic_teir=geographic_teir
        array_val=[10,25,50,50]
        index_lookup=tier_array.index(geographic_teir)
        requirement_val=array_val[index_lookup]
        minimum_jobs_bol="Yes" if promised_jos>=requirement_val else "No"


        ## main tab
        main_value=choose_with_condition("max","Yes",meets_array,QJTC_credit)

        main_bol="Yes" if (requirement_wages_bol=="Yes" and minimum_jobs_bol=="Yes") else "No"
        df_dict=defaultdict(list)
        year=5
        for i in range(year+1):
            df_dict["Year"].append(i)
            if main_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(promised_jos*main_value)
        self.sub_array=df_dict["value"]
        self.main_bol=main_bol

        return df_dict

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

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Georgia")
                value = i.replace("Georgia", "GA")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", GA")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
