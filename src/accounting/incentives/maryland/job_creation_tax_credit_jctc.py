import datetime

from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *
from datetime import date

from util.connecticut_config import  enterprise
from accounting.incentives.maine.employment_tax_increment_financing_program_etif import IncentiveProgram as subclass

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']
        self.all_input = kwargs

        self.pnl_input = kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.county=self.get_county_name()
        self.get_zone=self.get_zone()

        self.default_year = [i for i in range(11)]
        self.construction = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                              property_type=RealProperty.CONSTRUCTION_MATERIAL)

        self.machine = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        self.fix = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                     property_type=PersonalProperty.FIXTURES)
        self.high_level = self.project_level_inputs["High-level category"]
        self.irs = self.project_level_inputs["IRS Sector"]
        self.project_category = self.project_level_inputs["Project category"]
        self.promised_jobs = self.project_level_inputs["Promised jobs"]
        self.promised_wage = self.project_level_inputs["Promised wages"]
        self.promised_cap = self.project_level_inputs["Promised capital investment"]
        self.federal_minimum_wage = self.project_level_inputs["Federal minimum wage"]
        self.equipvalent_payroll_base = self.project_level_inputs["Equivalent payroll (BASE)"]
        self.discount_rate = self.project_level_inputs["Discount rate"]

        self.state_local_sale_tax_rate = self.pnl_input["state_local_sales_tax_rate"]
        self.rd = self.npv_dicts["Research & development"]
        self.total_real_and_personal_prop = self.construction + self.machine + self.fix
        self.total_personal_prop = self.fix + self.machine
        self.property_tax_rate = self.pnl_input["property_tax_rate"]
        self.property_tax = self.npv_dicts["Property tax"]
        self.annual_exp = self.npv_dicts["Annual capital expenditures option 2"]
        self.attraction = self.project_level_inputs["Attraction or Expansion?"]
        self.final_return_info = self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
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
                index = i.index(", Maryland")
                value = i.replace("Maryland", "MD")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", MD")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

    def final_return(self):

        ## state minimum wage
        promised_wage=self.project_level_inputs["Promised wages"]
        today=str(date.today().strftime("%m/%d/%Y"))
        array_val=[13.2,14.1,15,15.9,16.8,18]
        data_array=["1/1/2020","1/1/2021","1/1/2022","1/1/2023","1/1/2024","1/1/2025"]
        array_var=[]
        for i in data_array:
            start=datetime.datetime.strptime(today,"%m/%d/%Y")
            end=datetime.datetime.strptime(i,"%m/%d/%Y")
            dif=start.date()-end.date()
            dif=dif.days


            array_var.append(int(dif)**2)

        min_val=min(array_var)
        index_val=array_var.index(min_val)
        ## check with Sean about vlookup for date rows 2583

        choose_val=array_val[index_val]
        state_min_bol="Yes" if promised_wage/2000 >=choose_val*1.2 else "No"


        #location
        promised_job=self.project_level_inputs["Promised jobs"]
        zone_array=[self.zone_type_1,self.zone_type_2,self.zone_type_3]
        bol_zone="Yes" if zone_array.count("*JCTC*")>0 else "No"
        county_lookup=["Allegany","Charles","Somerset","Baltimore City","Dorchester","Talbot","Calvert","Garrett","Washington","Caroline","Kent","Wicomico","Carroll","Queen Anne's","Worcester","Cecil","Saint Mary's"]
        county_bol="Yes" if self.county in county_lookup else "No"

        localtion_bol_array=[
            "Yes" if promised_job>= 60 else "No",
            "Yes" if bol_zone=="Yes" and promised_job>=25 else "No",
            "Yes" if county_bol=="Yes" and promised_job>=10 else "No",
        ]

        main_location_bol="Yes" if localtion_bol_array.count("Yes")>0 else "No"


        ## benefit

        ## default standrd
        standard_value=3000

        #main
        self.main_bol="Yes" if main_location_bol=="Yes" and state_min_bol=="Yes" else "No"

        main_array=[min([1000000,promised_job*standard_value]) for i in range(11)]
        main_array[0]=0
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return  df_dict

