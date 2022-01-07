from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

from util.connecticut_config import  enterprise
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']
        self.all_input=kwargs
        self.county=self.get_county_name()
        # self.zone_type_1 = kwargs['zone_type_1']
        # self.zone_type_2 = kwargs['zone_type_2']
        # self.zone_type_3 = kwargs['zone_type_3']
        # self.get_zone = self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts

        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
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

    def final_return(self):
        #necessary variables
        irs_sector=self.project_level_inputs["IRS Sector"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        promised_wage=self.project_level_inputs["Promised wages"]
        promised_capital=self.project_level_inputs["Promised capital investment"]
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        construction_labor=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.CONSTRUCTION_LABOR)
        prevailing_wage=None
        state_local_tax_rate=self.pnl_input["state_local_sales_tax_rate"]
        anual_expenditure=self.npv_dicts["Annual capital expenditures option 2"]
        if isinstance(self.county,str):
            prevailing_wage=self.all_input["county_to_prevailing_wages"][self.county]
        else:
            prevailing_wage=self.all_input["state_to_prevailing_wages"]["Illinois"]

        ##requirement
        requirement_bol_array=[
            "Yes" if irs_sector=="Data processing, hosting, and related services" else "No",
            "Yes" if promised_jobs >=20 else "No",
            "Yes" if promised_wage>=prevailing_wage*1.2 else "No",
            "Yes" if promised_capital>=250000000 else "No"
        ]

        #main_tab
        main_bol="Yes" if requirement_bol_array.count("Yes")==4 else "No"
        self.main_bol=main_bol
        sales_tax_exemption_array=[]
        construction_tax_credit=[]
        main_array=[]
        construction_employment_bol="No"
        sales_tax_exemption_array=[]
        for i in range(11):
            if i==0:
                sales_tax_exemption_array.append(state_local_tax_rate*machinery)
            else:
                sales_tax_exemption_array.append(state_local_tax_rate*anual_expenditure[i])

            if construction_employment_bol=="Yes":
                construction_tax_credit.append(0.2*anual_expenditure[i])
            else:
                construction_tax_credit.append(0)
            if main_bol=="Yes":
                main_array.append(construction_tax_credit[-1]+sales_tax_exemption_array[-1])
            else:
                main_array.append(0)

        year=[i for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        df_dict["sales_tax_exmption"]=sales_tax_exemption_array
        return df_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Illinois")
                value = i.replace("Illinois", "IL")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", IL")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
