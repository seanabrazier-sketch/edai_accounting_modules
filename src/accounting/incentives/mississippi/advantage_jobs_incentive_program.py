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
        self.attraction=self.project_level_inputs["Attraction or Expansion?"]
        self.final_return_info=self.final_return()

    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        year = 5
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
                index = i.index(", Mississippi")
                value = i.replace("Mississippi", "MS")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", MS")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

        return county



    def final_return(self):

        prevailing_county=None
        prevailing_state=self.project_level_inputs["Prevailing wages"]["Mississippi"]
        if isinstance(self.county,str):
            prevailing_county=self.project_level_inputs["Prevailing wages county"][self.county.replace("MS","Mississippi")]
        else:
            prevailing_county=prevailing_state
        prevailing=min([prevailing_state,prevailing_county])
        data_it_array=[
            "Yes",
            "Yes" if self.irs=="Data processing, hosting, and related services" else "No",
            "Yes" if self.promised_jobs>=200 else "No",
            "Yes" if self.promised_wage>=prevailing else "No"
        ]
        data_it_bol="Yes" if data_it_array.count("Yes")==4 else "No"


        requirement_bol_array=[
            "Yes",
            "Yes" if self.promised_jobs>=25 else "No",
            "Yes" if self.promised_wage>=prevailing*1.1 else "No"
        ]

        requirement_bol="Yes" if requirement_bol_array.count("Yes")==3 else "No"

        ## benefit
        value_use=self.promised_wage*0.04*self.promised_jobs
        income_use=(290+0.05*(self.promised_wage-10000))/self.promised_wage

        #main
        array1=[self.promised_jobs*self.promised_wage*0.9*income_use for i in range(11)]
        array1[0]=0
        array2=[min([value_use,i]) for i in array1]
        self.main_bol=data_it_bol if data_it_array[1]=="Yes" else requirement_bol

        if self.main_bol=="Yes":
            main_array=array2
        else:
            main_array=[0 for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return  df_dict

