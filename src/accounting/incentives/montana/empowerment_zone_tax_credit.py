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
        # self.sub_class=subclass(**kwargs)
        self.capex = kwargs['capex']
        self.all_input=kwargs

        self.pnl_input = kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.default_year = [i for i in range(11)]
        self.construction = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                         property_type=RealProperty.CONSTRUCTION_MATERIAL)

        self.machine = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        self.fix = self.capex.amount(industry_type=self.pnl_input["industry_type"], property_type=PersonalProperty.FIXTURES)
        self.land=self.capex.amount(industry_type=self.pnl_input["industry_type"], property_type=RealProperty.LAND)


        self.high_level=self.project_level_inputs["High-level category"]
        self.irs=self.project_level_inputs["IRS Sector"]
        self.project_category=self.project_level_inputs["Project category"]
        self.promised_jobs=self.project_level_inputs["Promised jobs"]
        self.promised_wage=self.project_level_inputs["Promised wages"]
        self.promised_cap=self.project_level_inputs["Promised capital investment"]
        self.federal_minimum_wage=self.project_level_inputs["Federal minimum wage"]
        self.equipvalent_payroll_base=self.project_level_inputs["Equivalent payroll (BASE)"]
        self.discount_rate=self.project_level_inputs["Discount rate"]
        self.county=self.get_county_name()
        self.state_local_sale_tax_rate=self.pnl_input["state_local_sales_tax_rate"]
        self.rd=self.npv_dicts["Research & development"]
        self.total_real_and_personal_prop=self.construction+self.machine+self.fix
        self.total_personal_prop=self.fix  + self.machine
        self.property_tax_rate=self.pnl_input["property_tax_rate"]
        self.property_tax = self.npv_dicts["Property tax"]
        self.annual_exp=self.npv_dicts["Annual capital expenditures option 2"]
        self.annual_exp[0]=0
        self.attraction=self.project_level_inputs["Attraction or Expansion?"]
        self.state_corporate_income_tax = self.npv_dicts["State corporate income tax"]
        self.prevailing_wage_county=self.project_level_inputs["Prevailing wages county"]
        self.prevailing_state=self.project_level_inputs["Prevailing wages"]
        self.county_unemp=self.all_input["county_to_unemployment_rate"]
        self.state_unemp=self.all_input["state_to_unemployment_rate"]
        self.final_return_info=self.final_return()


    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        year = 4
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
                index = i.index(", Montana")
                value = i.replace("Montana", "MT")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", MT")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
    def final_return(self):
        #main
        var1=None
        if isinstance(self.county,str):
            county_poverty=list_of_special_localities["Poverty"][self.county]
        else:
            county_poverty=0

        pov_bol="Yes" if county_poverty>=self.all_input["state_to_poverty_rate"]["Montana"]*1.5 else "No"

        try:
            var1="Yes" if self.county_unemp[self.county]>self.state_unemp["Montana"]*1.5 else "No"
        except:
             var1="No"
        bol_array=[
            var1,
            pov_bol
        ]

        self.main_bol="Yes" if bol_array.count("Yes")>0 else "No"

        main_array=[self.promised_jobs*500 if self.main_bol=="Yes" else 0 for i in range(11)]
        main_array[0]=0
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict
