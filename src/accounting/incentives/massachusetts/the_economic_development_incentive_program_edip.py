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
        # self.sub_class = subclass(**kwargs)
        self.capex = kwargs['capex']
        self.all_input = kwargs

        self.pnl_input = kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
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

        self.rd = self.npv_dicts["Research & development"]

        self.final_return_info = self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
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




    def final_return(self):
        promised_job=self.project_level_inputs["Promised jobs"]
        attraction=self.project_level_inputs["Attraction or Expansion?"]
        job_to_use_bol_array=[
            "Yes" if  promised_job>=1 else "No",
            "Yes" if promised_job>=100 else "No",
            "Yes" if promised_job>=100 else "No",
            "Yes" if attraction=="Relocation" and promised_job>=25 else ("Yes" if attraction=="Expansion" and promised_job>=50 else "No")


        ]
        high_level=self.project_level_inputs["High-level category"]
        sector_use_bol="Yes" if high_level=="Manufacturing" else "No"
        capex_to_use_bol="Yes"
        geography_bol="Yes"

        eligible_bol_array=[
            job_to_use_bol_array[0],
            "Yes" if capex_to_use_bol=="Yes" and job_to_use_bol_array[1]=="Yes" else "No",
            job_to_use_bol_array[2],
            "Yes" if (job_to_use_bol_array[3]=="Yes" and sector_use_bol=="Yes" and geography_bol=="Yes") else "No"

        ]
        promised_capital=self.project_level_inputs["Promised capital investment"]

        array_value=[
            promised_capital*0.1 if eligible_bol_array[0]=="Yes" else 0 ,
            promised_capital*0.1 if eligible_bol_array[1]=="Yes" else 0 ,
            1000*promised_job if (geography_bol=="Yes" and eligible_bol_array[2]=="No" ) else (5000*promised_job if geography_bol=="Yes" and eligible_bol_array=="Yes" else 0),
            promised_capital*0.1369 ## this is in discretionary incentive cals ## need to embed in the model --> comback
        ]

        value_choose=choose_with_condition("max","Yes",eligible_bol_array,array_value)

        self.main_bol="Yes" if eligible_bol_array.count("Yes")>0 else "No"
        if self.main_bol=="Yes":
            main_array=[value_choose for i in range(11)]
        else:
            main_array=[0 for i in range(11)]
        main_array[0]=0
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict
