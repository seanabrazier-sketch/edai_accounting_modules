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


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

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





    def final_return(self):
        # real Property tax
        real_bol="No"
        land=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.LAND)
        construction=self.capex.amount(industry_type=self.pnl_input["industry_type"], property_type=RealProperty.CONSTRUCTION_MATERIAL)

        total_tax=land+construction
        property_tax=self.pnl_input["property_tax_rate"]
        if real_bol=="Yes":
            real_array=[total_tax*property_tax*0.8 for i in range(11)]
        else:
            real_array=[0 for i in range(11)]
        real_array[0]=0


        #personal_property tax
        personal_bol=real_bol
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        fixture=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.FIXTURES)
        total=machinery+fixture+construction
        if personal_bol=="Yes":
            per_array=[total*property_tax for i in range(11)]
        else:
            per_array=[0 for i in range(11)]

        per_array[0]=0

        ## Real property EZ
        real_ez_bol="Yes"
        default_rate=[0,0.8,0.8,0.8,0.8,0.8,0.7,0.6,0.5,0.4,0.3]
        if real_ez_bol=="Yes":
            real_ez_array=[property_tax*default_rate[i]*total_tax for i in range(11)]
        else:
            real_ez_array=[0 for i in range(11)]

        ## income tax credit Econ Disavantage leave out since assume no

        ## income tax credit
        federal_minimum_wage=self.project_level_inputs["Federal minimum wage"]
        promised_wage=self.project_level_inputs["Promised wages"]

        income_tax_credit_bol_array=[
            "Yes",
            "No",
            "Yes" if promised_wage/2080 > federal_minimum_wage*1.5 else "No"
        ]

        bol_or="Yes" if income_tax_credit_bol_array[0:1].count("Yes")>0 else "No"
        income_tax_bol="Yes" if bol_or=="Yes" and income_tax_credit_bol_array[-1]=="Yes" else "No"
        default_val=1000
        promised_job=self.project_level_inputs["Promised jobs"]
        income_tax_array=[promised_job*1000 for i in range(11)]
        income_tax_array[0]=0

        ## main
        self.main_bol="No"
        ez_array=[
            "No",
            "Yes"
        ]

        is_not_ez_array=[]
        for i in range(11):
            if ez_array[-1]=="Yes":
                if i ==0:
                    is_not_ez_array.append(0)
                else:
                    if i==1:
                        is_not_ez_array.append(income_tax_array[1]+real_ez_array[1])
                    else:
                        is_not_ez_array.append(real_ez_array[i])
            else:
                is_not_ez_array.append(0)



        ## leave out since need to integrate
        if self.main_bol=="Yes":
            main_array=is_not_ez_array
        else:

            main_array=[0 for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict



