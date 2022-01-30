from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']
        self.all_input=kwargs
        self.county=self.get_county_name()
        self.get_zone=self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]
        self.census_industry_earning_name=self.project_level_inputs["Census industry earnings name"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.irs=self.project_level_inputs["IRS Sector"]
        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
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
    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Kansas")
                value = i.replace("Kansas", "KS")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", KS")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

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
    def final_return(self):

        ## minimum capital investment
        state_specific=state_specific_sector
        state_specific.index=state_specific["IRS Returns of active corporations"].tolist()

        try:
            state_specific_value=state_specific["AL Property tax"][self.irs]
            if state_specific_value!="":
                state_specific_value="Yes"
            else:
                state_specific_value="No"

        except:
            state_specific_value="No"

        minimum_capital_investment_array=[
            state_specific_value,
            "Yes" if self.zone_type_1=="Urban" else "No"

        ]

        minimum_cap_bol="Yes" if minimum_capital_investment_array.count("Yes") >0 else "No"

        # sector requirement
        sector_requirement_bol_array=[
            state_specific_value,
            "Yes"
        ]
        sector_bol="Yes" if sector_requirement_bol_array.count("Yes")>0 else "No"

        ## minimum_training
        minimum_training_bol_array=[
            "Yes",
            "No",
            "No",
        ]
        minimum_bol="Yes" if minimum_training_bol_array.count("Yes")>0 else "No"

        #average wages

        ## load census ACS file


        ## get GEOID

        census_heading=census_acs_industrial_heading
        census_heading.index=census_heading["Full name"].tolist()
        header=census_heading["Table code"][self.census_industry_earning_name]

        earning_value=census_asc_industrial_earning
        earning_value.index=earning_value["NAME"]
        earning_value=earning_value[header]["Kansas"]



        industry_median_earning=earning_value


        ## error in excel for wrong linking to different state, Kansas State
        prevailing_wages=self.project_level_inputs["Prevailing wages"]["Kansas"]

        prommised_wages=self.project_level_inputs["Promised wages"]
        average_wages_bol_array=[
            "Yes" if prommised_wages>=industry_median_earning else "No",
            "Yes" if prommised_wages>=prevailing_wages*1.5 else "No"
        ]

        requirement_bol="Yes" if average_wages_bol_array.count("Yes")>0 else "No"

        ## main tab
        main_bol="Yes" if (minimum_bol=="Yes" and requirement_bol=="Yes" and sector_bol=="Yes" and minimum_cap_bol=="Yes") else "No"
        self.main_bol=main_bol
        construction_material=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.CONSTRUCTION_MATERIAL)
        machinery = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                                  property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        fixture = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                      property_type=PersonalProperty.FIXTURES)

        investment_tax_credit_array=[]
        main_array=[]
        year=[]
        sales_tax_exemption_on_equipment_array=[]
        sum_val=(construction_material+machinery+fixture)*0.1
        state_local_sales_tax=self.pnl_input["state_local_sales_tax_rate"]
        anual_exp=self.npv_dicts["Annual capital expenditures option 2"]
        sum_val_1=(construction_material+machinery)*state_local_sales_tax
        for i in range(11):
            year.append(i)
            if i ==0:
                investment_tax_credit_array.append(0)
                main_array.append(0)
                sales_tax_exemption_on_equipment_array.append(sum_val_1)
            else:
                if i==1:
                    investment_tax_credit_array.append(sum_val)
                else:
                    investment_tax_credit_array.append(0)
                sales_tax_exemption_on_equipment_array.append(anual_exp[i]*state_local_sales_tax)
                if main_bol=="Yes":
                    main_array.append(investment_tax_credit_array[-1]+sales_tax_exemption_on_equipment_array[-1])
                else:
                    main_array.append(0)
        df_dict=defaultdict(list)

        df_dict["year"]=year
        df_dict["value"]=main_array
        df_dict["Sales tax exemption on equipment"]=sales_tax_exemption_on_equipment_array
        return df_dict

