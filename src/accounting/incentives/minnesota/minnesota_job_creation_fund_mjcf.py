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
            zone_type_1 = list_of_special_localities()["Zone Type 1"]
            self.zone_type_1 = zone_type_1[self.county]
            if len(self.zone_type_1) == 0:
                self.zone_type_1 = "-"
        except:
            self.zone_type_1 = "-"
        try:
            zone_type_2 = list_of_special_localities()["Zone Type 2"]
            self.zone_type_2 = zone_type_2[self.county]
            if len(self.zone_type_2) == 0:
                self.zone_type_2 = "-"
        except:
            self.zone_type_2 = "-"
        try:
            zone_type_3 = list_of_special_localities()["Zone Type 3"]
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
                index = i.index(", Minnesota")
                value = i.replace("Minnesota", "MN")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", MN")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county


    def final_return(self):

        ## requiremnet if not twin
        if_not_twin_array=[
            "Yes" if self.promised_cap>=250000 else "No",
            "Yes" if self.promised_jobs>=5 else "No",
            "Yes" if self.promised_jobs>=75 and self.promised_cap>=25000000 else "No"
        ]

        zone2_bol="Yes" if self.zone_type_2=="Seven county MSP" else "No"
        require_not_twin_bol="Yes" if if_not_twin_array[0:2].count("Yes")==2 and zone2_bol=="No" else "No"

        ## require if twin

        if_twin_array=[
            "Yes" if self.promised_cap>=500000 else "No",
            "Yes" if self.promised_jobs>=10 else "No",
            "Yes" if self.promised_jobs>=200 and self.promised_cap>=25000000 else 'No'
        ]
        twin_bol="Yes" if if_twin_array[0:1].count("Yes")==2 and self.zone_type_2=="Seven county MSP" else "No"

        #main_requirement
        requirement_array_bol=[
            "Yes" if self.high_level=="Information" else "No",
            "Yes" if self.high_level=="Manufacturing" else "No",
            "Yes" if self.project_category=="Distribution center" else "No",
            "Yes" if self.promised_wage/2080 >=13.61 else "No"
        ]
        ## benefit
        in_twin="Yes" if self.zone_type_2=="Seven county MSP" else 'No'

        benefit_bol_array=[
            'Yes' if in_twin=="Yes" and twin_bol=="Yes" else "No",
            "Yes" if in_twin=="Yes" and require_not_twin_bol=="Yes" else "No"
        ]


        ## benefit wage grant
        benefit_wage_bol_array=[
            "Yes" if self.promised_wage>=28427 else "No",
            "Yes" if self.promised_wage>=38263 else "No",
            "Yes" if self.promised_wage>=49194 else "No"
        ]

        array_value=[1000,2000,3000]
        choose_val=choose_with_condition("max","Yes",benefit_wage_bol_array,array_value)


        ## main
        bol_main_req="Yes" if requirement_array_bol.count("Yes")>0 else "No"
        bol_1="Yes" if twin_bol=="Yes" or require_not_twin_bol=="Yes" else "No"

        self.main_bol="Yes" if bol_main_req=="Yes" and bol_1=="Yes" else "No"
        max_payout_bol="Yes" if require_not_twin_bol[-1]=="Yes" or if_not_twin_array[-1]=="Yes" else "No"

        max_payout_val=1000000 if max_payout_bol=="Yes" else 500000

        array1=[]
        array2=[]
        array3=[]
        main_array=[]
        for i in range(11):
            if self.main_bol=="Yes":
                if i ==1:
                    if benefit_bol_array[0]=="Yes":
                        array2.append(min([max_payout_val,self.construction*0.05]))
                    else:
                        array2.append(0)
                    if benefit_bol_array[-1]=="Yes":
                        array1.append(min([max_payout_val,0.075*self.construction]))
                    else:
                        array1.append(0)
                    array3.append(min([choose_val*self.promised_jobs,max_payout_val]))
                    main_array.append(array1[-1]+array2[-1]+array3[-1])
                else:
                    array1.append(0)
                    array2.append(0)
                    array3.append(0)
                    main_array.append(array1[-1] + array2[-1] + array3[-1])
            else:
                main_array.append(0)


        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return  df_dict
