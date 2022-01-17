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
        self.rd=self.npv_dicts["Research & development"]

        self.final_return_info=self.final_return()
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





    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Michigan")
                value = i.replace("Michigan", "MI")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", MI")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

    def final_return(self):
        sector_bol="Yes"
        ## mising county population need to embed
        # default for now
        county_pop=None
        if isinstance(self.county,str):
            county_pop=list_of_special_localities["Poverty"][self.county]
        else:
            county_pop=0
        county_unemp=None
        state_unemp=self.all_input["state_to_unemployment_rate"]["Michigan"]
        if isinstance(self.county,str):
            county_unemp=self.all_input["county_to_unemployment_rate"][self.county]
        else:

            county_unemp=0
        ## the formula need to be check at row Q2828 since no county it still return Yes

        eligible_sub_bol_array=[
            "Yes" if self.irs=="Transportation equipment manufacturing" else "No",
            "Yes" if self.irs == "Transportation equipment manufacturing" else "No",
            "Yes" if self.irs=="Agricultural production" else "No",
            "Yes" if self.high_level=="Manufacturing" else "No"
        ]

        sub_bol_array=[
            "Yes" if county_pop>25000 and county_unemp>state_unemp else "No",
            "Yes",
            "Yes" if eligible_sub_bol_array.count("Yes")>0 else "No",
        ]
        sub_bol_val="Yes" if sub_bol_array[1:2].count("Yes")==2 and self.promised_jobs<=50 else "No"
        eligibile_bol_array=[
            "Yes" if self.promised_jobs>=50 else "No",
            "Yes" if self.promised_jobs>=25 or sector_bol=="Yes" else "No",
            "Yes" if sub_bol_val=="Yes" and sub_bol_array[0]=="Yes" else "No"
                             ]


        ## discretionary Incentives cals not yet embed --> default for now
        # ask Sean if this can be default
        array_value=[9903,14879,25693]
        choose_value=choose_with_condition("max","Yes",eligibile_bol_array,array_value)
        self.main_bol="Yes" if eligibile_bol_array.count("Yes")>0 else "No"
        if self.main_bol=="Yes":
            main_array=[min([10000000,self.promised_jobs*choose_value]) for i in range(11)]
        else:
            main_array=[0 for i in range(11)]
        df_dict=defaultdict(list)
        main_array[0]=0
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict
