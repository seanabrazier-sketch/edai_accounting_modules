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
        self.zone_type_1 = kwargs['zone_type_1']
        self.zone_type_2 = kwargs['zone_type_2']
        self.zone_type_3 = kwargs['zone_type_3']
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
        promised_jobs=self.project_level_inputs["Promised jobs"]
        promised_wage=self.project_level_inputs["Promised wages"]
        state_corporate_tax=self.npv_dicts["State corporate income tax"][1:]
        state_local_sales_tax=self.npv_dicts["State/local sales tax"][1:]
        county_prevailing_wages=None

        if isinstance(self.county,str):
            county_prevailing_wages=self.project_level_inputs['Prevailing wages county'][self.county]
        else:

            county_prevailing_wages=self.project_level_inputs["Prevailing wages"]["Idaho"]

        ##benfit
        cap_with_holding=[promised_wage*promised_jobs*0.0693 for i in range(10)]
        state_tax_liability=[sum([i,j,k]) for i,j,k in zip(state_corporate_tax,state_local_sales_tax,cap_with_holding)]

        ## requirement
        default_pop=0
        ## need to raise this to Sean the check in the excel sheet is wrong
        rural_urban="Rural" if default_pop<25000 else "Urban"
        requirement_bol_array=[
            rural_urban,
            "Yes" if (rural_urban=="Rural" and promised_jobs>=20) else "No",
            "Yes" if (rural_urban=="Urban" and promised_jobs>=50) else "No",
            "Yes" if (promised_wage>=county_prevailing_wages) else "No",
            "Yes"

        ]

        ## main tab
        ### ask Sean to check upon this on the excel Sheet on the main bol

        #default yes for now
        bol1=requirement_bol_array[2] if rural_urban=="Urban" else requirement_bol_array[1]

        main_bol="Yes" if (requirement_bol_array[3]=="Yes" and bol1=="Yes") else "No"



        df_dict=defaultdict(list)
        for i in range(11):
            df_dict["Year"].append(i)
            if main_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(cap_with_holding[i-1]*0.21)
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
                index = i.index(", Idaho")
                value = i.replace("Idaho","ID")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", ID")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county


