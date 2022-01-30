from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

from accounting.incentives.maine.employment_tax_increment_financing_program_etif import IncentiveProgram as subclass

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sub_class=subclass(**kwargs)
        self.capex = kwargs['capex']
        self.all_input=kwargs
        self.county=self.get_county_name()

        self.discount_rate = self.project_level_inputs["Discount rate"]

        self.get_zone = self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.default_year=[i for i in range(11)]
        self.final_return_info=self.final_return()
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
                index = i.index(", Maine")
                value = i.replace("Maine", "ME")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", ME")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county



    def final_return(self):
        # sales use and tax
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        construciton=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.CONSTRUCTION_MATERIAL)
        state_local_sales=self.pnl_input["state_local_sales_tax_rate"]
        anual_exp=self.npv_dicts["Annual capital expenditures option 2"]
        sale_1=[]
        sale_2=[]
        sale_3=[]

        for i in range(11):
            if i ==0:
                sale_1.append(construciton*state_local_sales)
                sale_2.append(machinery * state_local_sales)
            else:
                sale_1.append(0)
                sale_2.append(state_local_sales*anual_exp[i])

            sale_3.append(sale_1[-1]+sale_2[-1])
        ## employment_tax
        sub_class_array=self.sub_class.main_array


        # coporate Income
        coporate_bol_array=[
            "Yes" if self.zone_type_1=="Pine Tree Development Zone" else "No",
        ]
        coporate_bol_array.append("Yes" if coporate_bol_array[-1]=="No" else "No")
        state_corporate=self.npv_dicts["State corporate income tax"]
        cop_1=[]
        cop_2=[]
        cop_3=[]
        rate1=[0,1,1,1,1,1,0,0,0,0,0]
        rate2=[0,1,1,1,1,1,0.5,0.5,0.5,0.5,0.5]
        for i in range(11):
            cop_1.append(rate1[i]*state_corporate[i])
            cop_2.append(rate2[i]*state_corporate[i])

            if coporate_bol_array[0]=="Yes":
                cop_3.append(cop_2[-1])
            else:
                cop_3.append(cop_1[-1])

        ## eligible sector
        high_level=self.project_level_inputs["High-level category"]
        irs=self.project_level_inputs["IRS Sector"]
        lista=["Finance and insurance total","Credit intermediation","Credit intermediation","Securities, commodity contracts, other financial investments, and related activities","Insurance carriers and related activities"]

        eligible_bol_array=[
            "Yes" if high_level=="Information" else "No",
            "Yes" if high_level=="Manufacturing" else "No",
            "Yes" if irs in lista else "No"
        ]

        eligible_bol="Yes" if eligible_bol_array.count("Yes")>0 else "No"
        county_capital=None
        try:
            county_capital=self.all_input["county_to_per_capita_income"][self.county]
        except:
            county_capital=self.all_input["state_to_per_capita_income"]["Maine"]
        ## requirement
        promised_capital=self.project_level_inputs["Promised capital investment"]
        promised_wage=self.project_level_inputs["Promised wages"]
        promised_job=self.project_level_inputs["Promised jobs"]
        requirement_bol_array=[
            "Yes" if promised_wage>county_capital else "No",
            "Yes" if eligible_bol_array[1]=="Yes" and promised_capital>=225000 else ("Yes" if eligible_bol_array[1]=="No" else "No"),
            "Yes" if eligible_bol_array[1]=="No" and promised_job>=1 else ("Yes" if eligible_bol_array[1]=="Yes" and promised_job>=4 else "No")

        ]
        requirement_bol="Yes" if requirement_bol_array.count("Yes")==3 else "No"

        ## Main
        self.main_bol="Yes" if requirement_bol=="Yes" and eligible_bol=="Yes" else "No"

        tier=None
        if coporate_bol_array[0]=="Yes":
            tier="Tier One"
        else:
            if coporate_bol_array[1]=="Yes":
                tier="Tier Two"
            else:
                tier="n/a"
        main_array=[]

        for i in range(11):
            if self.main_bol=="Yes":
                if i ==0:
                    main_array.append(sale_3[i]+cop_3[i]+sub_class_array[i])
                else:
                    if tier=="Tier One":
                        value=cop_2[i]
                    else:
                        value=cop_1[i]


                    main_array.append(sale_3[i]+sub_class_array[i]+value)
            else:
                main_array.append(0)
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict