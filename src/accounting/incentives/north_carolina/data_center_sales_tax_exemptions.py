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
        self.county = self.get_county_name()
        self.get_zone = self.get_zone()
        self.pnl_input = kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.default_year = [i for i in range(11)]
        self.construction = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                              property_type=RealProperty.CONSTRUCTION_MATERIAL)

        self.machine = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        self.fix = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                     property_type=PersonalProperty.FIXTURES)
        self.land = self.capex.amount(industry_type=self.pnl_input["industry_type"], property_type=RealProperty.LAND)

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
        self.annual_exp[0] = 0
        self.attraction = self.project_level_inputs["Attraction or Expansion?"]
        self.state_corporate_income_tax = self.npv_dicts["State corporate income tax"]
        self.prevailing_wage_county = self.project_level_inputs["Prevailing wages county"]
        self.prevailing_state = self.project_level_inputs["Prevailing wages"]
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

    def get_zone(self):

        try:
            zone_type_1 = list_of_special_localities["Zone Type 1"]
            self.zone_type_1 = zone_type_1[self.county]
        except:
            self.zone_type_1 = "-"
        try:
            zone_type_2 = list_of_special_localities["Zone Type 2"]
            self.zone_type_2 = zone_type_2[self.county]
        except:
            self.zone_type_2 = "-"
        try:
            zone_type_3 = list_of_special_localities["Zone Type 3"]
            self.zone_type_3 = zone_type_3[self.county]
        except:
            self.zone_type_3 = "-"

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", North Carolina")
                value = i.replace("North Carolina", "NC")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", ND")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

    def final_return(self):
        prevailing = None
        if isinstance(self.county,str):
            prevailing = self.prevailing_wage_county[self.county.replace("NC","North Carolina")]
        else:

            prevailing = self.prevailing_state["North Carolina"]
        #qualifying data center
        qualify_array_bol=[
            "Yes" if self.irs=="Data processing, hosting, and related services" else "No",
            "Yes" if self.promised_cap>=75000000 else "No",
            "Yes" if self.promised_wage>=prevailing else "No"
        ]
        qualify_bol="Yes"  if qualify_array_bol.count("Yes")==3 else "No"
        county = None
        tier_array = ["Tier 1", "Tier 2", "Tier 3", "High-Yield Project (HYP)", "Transformative Project"]
        if len(self.county) == 0:
            county = "None selected"
        else:
            county = self.county
        if county == "None selected":

            tier = "Tier 3"
        else:
            try:

                tier_array.index(self.zone_type_2)
            except:
                tier = "Tier 2"

        ## eligible internet data center
        eligibol_bol_array=[
            "Yes" if self.irs=="Data processing, hosting, and related services" else "No",
            "Yes" if self.promised_cap>=250000000 else "No",
            "Yes" if self.promised_wage>=prevailing else "No",
            "Yes" if tier=="Tier 1" or tier=="Tier 2" else "No"
        ]

        eligibol_bol="Yes" if eligibol_bol_array.count("Yes")==4 else "No"

        self.main_bol="Yes" if eligibol_bol=="Yes" or qualify_bol=="Yes" else "No"

        if self.main_bol == "Yes":
            main_array = [self.state_local_sale_tax_rate * self.annual_exp]
            main_array[0] = self.machine * self.state_local_sale_tax_rate
        else:
            main_array = [0 for i in range(11)]
        df_dict = defaultdict(list)
        df_dict["year"] = self.default_year
        df_dict["value"] = main_array
        return df_dict