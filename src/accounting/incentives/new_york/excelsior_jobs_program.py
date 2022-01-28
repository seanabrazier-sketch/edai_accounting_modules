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
        self.county = self.get_county_name()
        self.get_zone = self.get_zone()
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
        self.rd_tax=self.rd_tax_credit()
        self.final_return_info=self.final_return()
    def rd_tax_credit(self):
        array1=[i*0.06 for i in self.rd][0:4]
        array1[0]=0
        for i in range(1,8):
            value=(sum(self.rd[i:i+3])/3)*0.5
            value=self.rd[i+3]-value
            value=value*0.14
            array1.append(value)
        return array1
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
                index = i.index(", New York")
                value = i.replace("New York", "NY")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", NY")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
    def final_return(self):
        ## minimum_jobs
        # missing IRS P&L
        irs_specific_sector=irs_pl_state_special_sector
        irs_specific_sector.index=irs_pl_state_special_sector["IRS P&L"].tolist()
        value_check=None
        value_check2=None
        value_check3=None
        value_check4=None
        try:
            value_check=irs_specific_sector["New York"][self.irs]
            if value_check=="Agriculture":
                value_check="Yes"
            else:
                value_check="No"
        except:
            value_check="No"
        try:
            value_check2 = irs_specific_sector["New York"][self.irs]
            if value_check2=="Back office":
                value_check2="Yes"
            else:
                value_check2="No"
        except:
            value_check2="No"
        try:
            value_check3 = irs_specific_sector["New York"][self.irs]
            if value_check3 == "Entertainment":
                value_check3 = "Yes"
            else:
                value_check3 = "No"
        except:
            value_check3 = "No"
        try:
            value_check4 = irs_specific_sector["New York"][self.irs]
            if value_check4 == "PST services":
                value_check4 = "Yes"
            else:
                value_check4 = "No"
        except:
            value_check4 = "No"


        minimum_job_array=[
            "Yes" if self.promised_jobs>5 and self.project_category=="R&D Center" else "No",
            "Yes" if self.promised_jobs>5 and self.project_category=="Information" else "No",
            "No",
            value_check,
            "Yes" if self.promised_jobs>5 and self.high_level=="Manufacutring" else "No",
            value_check2,
            "Yes" if self.promised_jobs>50 and self.project_category=="Distribution center" else "No",
            value_check3,
            value_check3,
            value_check4

        ]
        ifnot_above_bol="Yes" if minimum_job_array.count("No")==10 and self.promised_jobs>=150 and self.promised_cap>=3000000 else "No"

        self.main_bol="Yes" if minimum_job_array.count("Yes")>0 or ifnot_above_bol=="Yes" else "No"

        #meet industry tab
        meet_industry_array=[
            ("Yes" if self.project_category=="R&D Center" else "No",
             "Yes" if self.promised_jobs>=10 else "No",
             "Yes" if self.promised_cap>=3000000 else "No"
             )
        ]
        meet_all_3_array=["Yes" if meet_industry_array[0].count("Yes")==3 else "No" for i in range(11)]
        real_prop_bol_array=[
            "No",
            "Yes" if meet_all_3_array.count("Yes")>0 else "No"

        ]
        real_prop_bol="Yes" if real_prop_bol_array.count("Yes")>0 else 'No'
        sum_val=self.land+self.construction
        #main
        real_prop_array=[self.property_tax_rate*sum_val if real_prop_bol=="Yes" else 0 for i in range(11)]
        real_prop_array[0]=0

        df_dict=defaultdict(list)
        df_dict["Real property tax credit"]=real_prop_array
        sum_val2=self.machine+self.construction
        ## RD tax credit
        array_tax_credit=[i*0.5 for i in self.rd_tax]
        array_tax_credit_main=[i*0.06 for i in array_tax_credit]
        df_dict["R&D tax credit"]=array_tax_credit_main

        investment_tax_credit_array=[sum_val2*0.02 if self.main_bol=="Yes" else 0 for i in range(11)]
        investment_tax_credit_array[0]=0
        df_dict["Investment tax credit"]=investment_tax_credit_array

        #job tax credit
        job_tax_credit_array=[self.promised_wage*self.promised_jobs*0.0685 if self.main_bol=="Yes" else 0 for i in range(11)]
        job_tax_credit_array[0]=0
        df_dict["Jobs tax credit"]=job_tax_credit_array
        if self.main_bol=="Yes":
            main_array=[i+j+k+l for i,j,k,l in zip(investment_tax_credit_array,job_tax_credit_array,real_prop_array,array_tax_credit_main)]
        else:
            main_array=[0 for i in range(11)]
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array

        return df_dict
