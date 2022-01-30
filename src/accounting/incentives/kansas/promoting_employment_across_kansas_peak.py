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
        self.get_zone=self.get_zone()


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
        year = self.main_year
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
    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Kansas")
                value = i.replace("Kansas", "KS")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", KS")
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
        #necessary variable
        promised_wage=self.project_level_inputs["Promised wages"]
        promised_job=self.project_level_inputs["Promised jobs"]
        zonetype1=self.zone_type_1
        prevailing_wage=None
        if isinstance(self.county,str):
            prevailing_wage=self.project_level_inputs["Prevailing wages county"][self.county]
        else:
            prevailing_wage=self.project_level_inputs["Prevailing wages"]["Kansas"]


        ## high impact
        high_impact_first_array=[
            "Yes" if promised_wage>=prevailing_wage else "No",
            "Yes" if promised_wage >= prevailing_wage*1.1 else "No",
            "Yes" if promised_wage >= prevailing_wage*1.2 else "No",
            "Yes" if promised_wage >= prevailing_wage*1.4 else "No",
        ]
        array_value=[1,1.1,1.2,1.4]
        value_lookup=choose_with_condition("max","Yes",high_impact_first_array,array_value)

        high_impact_bol_array=[
            "Yes" if promised_job>=100 else "No",
            value_lookup
        ]
        high_impact_year_array=[7,8,9,10]
        index_value=array_value.index(value_lookup)
        high_impact_year=high_impact_year_array[index_value]
        ## years based on median county
        median_county_bol_array=[
            "Yes" if promised_wage>=prevailing_wage else "No",
            "Yes" if promised_wage>= prevailing_wage*1.1 else "No",
            "Yes" if promised_wage>= prevailing_wage*1.2 else "No",
        ]

        year_array=[5,6,7]

        array_value1=[1,1.1,1.2]
        value_lookup=choose_with_condition("max","Yes",median_county_bol_array,array_value1)

        index=array_value1.index(value_lookup)
        median_year=year_array[index]

        #minimum Jobs
        minimum_job_array=[
            "Yes" if (zonetype1=="Urban" and promised_job>=10) else "No",
            "Yes" if (zonetype1!="Urban" and promised_job>=5) else "No"
        ]
        minimum_bol="Yes" if (minimum_job_array.count("Yes")>0) else "No"


        ## main_tab
        main_bol= "Yes" if (minimum_bol=="Yes" and median_county_bol_array.count("Yes")>0) else "No"
        main_year=high_impact_year if high_impact_bol_array[0]=="Yes" else median_year
        main_array=[]
        df_dict = defaultdict(list)

        for i in range(11):

            if main_bol=="Yes":
                main_array.append(promised_wage*promised_job*0.95*0.057)
            else:
                main_array.append(0)
        main_array[0]=0
        self.main_year=main_year
        df_dict["value"]=main_array
        self.main_bol=main_bol
        return df_dict

