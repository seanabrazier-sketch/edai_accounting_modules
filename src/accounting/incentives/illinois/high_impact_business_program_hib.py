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
        # self.county=self.get_county_name()
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
        ##necessary variables
        construction=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.CONSTRUCTION_MATERIAL)
        machinery = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        anual_expenditure=self.npv_dicts["Annual capital expenditures option 2"]
        state_local_sales_tax=self.pnl_input["state_local_sales_tax_rate"]
        sum_val=construction+machinery

        ##benefit
        sales_tax_exemption_array=[]
        investment_tax_credit_array=[]
        for i in range(11):
            if i==0:
                investment_tax_credit_array.append(0)
                sales_tax_exemption_array.append(state_local_sales_tax*sum_val)
            else:
                sales_tax_exemption_array.append(state_local_sales_tax*anual_expenditure[i])
                if i==1:
                    investment_tax_credit_array.append(0.005*sum_val)
                else:
                    investment_tax_credit_array.append(0)

        #main_tab:
        ##main_bol is default for now since Sean need to figure out
        eligibility_bol=[
            "Yes" if self.project_level_inputs["Promised jobs"]>=500 and self.project_level_inputs["Promised capital investment"]>=12000000 and self.project_level_inputs["Attraction or Expansion?"]=="Relocation" else "No"
            "Yes" if self.project_level_inputs["Promised jobs"]>=1500 and self.project_level_inputs["Promised capital investment"]>=30000000 and self.project_level_inputs["Attraction or Expansion?"]=="Relocation" else "No"

        ]
        main_bol="Yes" if eligibility_bol.count("Yes")>0 else "No"
        self.main_bol=main_bol
        year=[i for i in range(11)]
        main_array=[]
        for i in range(11):
            if main_bol=="Yes":
                main_array.append(investment_tax_credit_array[i]+sales_tax_exemption_array[i])
            else:
                main_array.append(0)
        main_array[0]=0

        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        return df_dict




