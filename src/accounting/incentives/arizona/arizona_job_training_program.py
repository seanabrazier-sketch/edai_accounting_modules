from accounting.incentives import *
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
        self.get_zone=self.get_zone()

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
        year = 2

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

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Arizona")
                value = i.replace("Arizona", "AZ")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", AZ")
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

    def final_return(self):
        #Incentive amount
        promised_jobs=self.project_level_inputs["Promised jobs"]
        rural="Yes" if self.zone_type_1=="Rural" else "No"
        fewer_than_100="Yes" if promised_jobs<=100 else "No"
        special_case="Yes" if (rural=="Yes" or fewer_than_100=="Yes") else "No"
        payout=8000 if special_case=="Yes" else 5000

        #elegible
        county = self.county



        if isinstance(county,str):

            maricopa_pima = "Yes" if (county == "Maricopa County" or county == "Pima County") else "No"
        else:
            maricopa_pima="No"

        promised_wages=self.project_level_inputs["Promised wages"]

        prevailing_wages=self.project_level_inputs['Prevailing wages']["Arizona"]

        all_other_counties="Yes" if (maricopa_pima=="No" and promised_wages>=0.8*prevailing_wages) else "No"
        in_maricopima_less="Yes" if(maricopa_pima=="Yes" and promised_jobs<100 and promised_wages>=0.8*prevailing_wages) else "No"
        in_maricopima_greater= "Yes" if (
                    maricopa_pima == "Yes" and promised_jobs >= 100 and promised_wages >= 0.8 * prevailing_wages) else "No"
        meet_requirement="Yes" if (all_other_counties=="Yes" or in_maricopima_greater=="Yes" or in_maricopima_less=="Yes") else "No"

        grant_estimate=grant_estimates_misc_2_df["Average Cost per trainee"]["Arizona Job Training Program"]



        # default dict
        df_dict=defaultdict(list)
        for i in range(2):
            df_dict["year"].append(i)
            if meet_requirement=="No":
                df_dict["value1"].append(0)
                df_dict["Value2"].append(0)
            else:
                if i==0:
                    df_dict["value1"].append(0)
                    df_dict["value2"].append(0)
                else:
                    array=[3000000,payout*promised_jobs]
                    df_dict["value"].append(promised_jobs*grant_estimate)

        self.main_bol=meet_requirement
        return df_dict
