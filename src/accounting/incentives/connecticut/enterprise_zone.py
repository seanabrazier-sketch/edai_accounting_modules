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

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
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
                index = i.index(", Connecticut")
                value = i.replace("Connecticut", "CT")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", CT")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

    def final_return(self):
        #necessary input
        df_dict=defaultdict(list)
        high_level_category=self.project_level_inputs["High-level category"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        state_corporate_income=self.npv_dicts['State corporate income tax']
        project_category=self.project_level_inputs["Project category"]


        #eligible
        #missing poverty
        #make a default boolean first
        county_poverty=None
        if isinstance(self.county,str):

            county_poverty=list_of_special_localities()["Poverty"][self.county]
        else:
            county_poverty=0
        #check if county exists
        if isinstance(self.county,str):

        #county unemployment rate
            county_to_unemployment_rate=self.all_input["county_to_unemployment_rate"][self.county]
        else:
            county_to_unemployment_rate=0
        poverty="Yes" if county_poverty>=0.25 else "No"



        state_poverty=self.all_input["state_to_poverty_rate"]["Connecticut"]
        ## this is an error in the excelsheet need to raise it up to Sean
        # this is default for now need to add poverty for ocunty
        poverty_rate_at_least_25=poverty

        unemployment_rate_at_least_200="Yes" if county_to_unemployment_rate>=state_poverty*2 else "No"
        population_assistance="Not modeled"
        eligibility_bol="Yes" if (poverty=="Yes" and unemployment_rate_at_least_200=="Yes") else "No"
        project_meets_bol="Yes" if (eligibility_bol=="Yes" or poverty_rate_at_least_25=="Yes") else "No"
        # Business eligibility, not intergated
        minimum_jobs_manufacturing_bol="Yes" if high_level_category=="Manufacturing" else "No"
        manufacturing_rate=0.25

        minimum_jos_service_facility_bol=  "No" if minimum_jobs_manufacturing_bol=="Yes" else "No"
        matching_array=[0,300,600,900,1200,1500,2000]
        return_array=[0,0.15,0.2,0.25,0.3,0.4,0.5]
        minimum_jobs_service_facility_rate=v_lookup_2(promised_jobs,matching_array,return_array)
        ## Business eligibility:
        business_elgibility_bol_array=["Yes" if high_level_category=="Manufacturing" else "No", "Yes" if project_category=="Distribution center" else "No", "Yes" if project_category=="R&D center" else "No", "No"]
        business_elgibility_yes_count=business_elgibility_bol_array.count("Yes")
        business_eligibility_bol="Yes" if business_elgibility_yes_count>0 else "No"


        # Benefit
        benefit_default_bol="Yes"
        property_tax=self.npv_dicts["Property tax"]
        machinary=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        state_local_sale_tax= self.pnl_input["state_local_sales_tax_rate"]
        year=10
        benefit_real_array=[]
        for i in range(year+1):
            if benefit_default_bol=="No":
                benefit_real_array.append(0)
            else:

                if i==0:
                    benefit_real_array.append(0)
                elif i<6:
                    benefit_real_array.append(property_tax[i])
                else:
                    benefit_real_array.append(0)
        #benefit _real is done
        df_dict["Real and personal property abtement"]=benefit_real_array
        benefit_corporate_array=[0]
        corporate_default_bol="Yes"
        corporate_income_tax_credit_rate=manufacturing_rate if minimum_jobs_manufacturing_bol=="Yes" else (minimum_jobs_service_facility_rate if minimum_jos_service_facility_bol=="Yes" else 0)
        for i in range(1,11):
            if corporate_default_bol=="No":
                benefit_corporate_array.append(0)
            else:
                benefit_corporate_array.append(corporate_income_tax_credit_rate*state_corporate_income[i])
        ## need to check upon this array, there is small difference
        df_dict["Corporate income tax credit"]=benefit_corporate_array

        ## main

        main_bol="Yes" if (project_meets_bol=="Yes" and business_eligibility_bol=="Yes") else "No"
        main_array=[0]
        for i in range(len(benefit_real_array)):
            if main_bol=="No":
                main_array.append(0)
            else:
                main_array.append(sum([benefit_real_array[i],benefit_corporate_array[i]]))
        df_dict["value"]=main_array
        self.main_bol=main_bol
        return df_dict









    def get_county_name(self):
        county=[]
        county_list=self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index=i.index(", AL")
                county.append(i)
                break
            except:
                pass

        if len(county)>0:
            county=county[0]
        else:
            county

        return county
    # def get_zone(self):
    #     try:
    #         self.zone_type_1=self.zone_type_1[self.county]
    #     except:
    #         self.zone_type_1="-"
    #     try:
    #         self.zone_type_2=self.zone_type_2[self.county]
    #     except:
    #         self.zone_type_2="-"
    #     try:
    #         self.zone_type_3=self.zone_type_3[self.county]
    #     except:
    #         self.zone_type_3="-"