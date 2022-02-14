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

        self.state_local_sale_tax_rate=self.pnl_input["state_local_sales_tax_rate"]
        self.rd=self.npv_dicts["Research & development"]
        self.total_real_and_personal_prop=self.construction+self.machine+self.fix
        self.total_personal_prop=self.fix  + self.machine
        self.property_tax_rate=self.pnl_input["property_tax_rate"]
        self.property_tax = self.npv_dicts["Property tax"]
        self.annual_exp=self.npv_dicts["Annual capital expenditures option 2"]
        self.attraction=self.project_level_inputs["Attraction or Expansion?"]
        self.state_corporate_income_tax = self.npv_dicts["State corporate income tax"]
        self.final_return_info=self.final_return()

    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        year = 10
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
        state_prevailing_wage=self.project_level_inputs["Prevailing wages"]

        state_prevailing_wage=state_prevailing_wage["Mississippi"]

        ## requirement
        requirement_array=[
            "Yes" if self.irs=="Data processing, hosting, and related services" else "No",
            "Yes" if self.promised_cap>=20000000 else "No",
            "Yes" if self.promised_jobs>=20 else "No",
            "Yes" if self.promised_wage>=state_prevailing_wage*1.25 else "No"
        ]
        req_bol="Yes" if requirement_array.count("Yes")==4 else "No"
        self.main_bol=req_bol
        if self.main_bol=="Yes":
            main_array=[i*self.state_local_sale_tax_rate for i in self.annual_exp]
            main_array[0]=self.state_local_sale_tax_rate*self.machine
        else:
            main_array=[0 for i in range(11)]


        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict
