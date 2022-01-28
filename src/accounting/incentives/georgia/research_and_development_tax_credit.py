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
        # self.county=self.get_county_name()
        # self.zone_type_1 = kwargs['zone_type_1']
        # self.zone_type_2 = kwargs['zone_type_2']
        # self.zone_type_3 = kwargs['zone_type_3']
        # self.get_zone = self.get_zone()
        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts

        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol == "Yes":
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
    def final_return(self):
        ##necessary variables
        high_level_category=self.project_level_inputs["High-level category"]
        project_category=self.project_level_inputs["Project category"]
        irs_sector=self.project_level_inputs["IRS Sector"]
        sales=self.npv_dicts["Sales"]
        sales=sales[1:]
        research_and_development=self.npv_dicts["Research & development"]
        research_and_development=research_and_development[1:]

        state_corporate_income_tax_rate=self.pnl_input["state_corporate_income_tax_apportionment"]
        # state_corporate_income_tax_rate=0.0319
        df_dict=defaultdict(list)
        ## requirement
        requirement_array_bol=[
            "Yes" if high_level_category=="Manufacturing" else "No",
            "Yes" if project_category=="Distribution center" else "No",
            "Yes" if project_category=="Call Center" else "No",
            "Yes" if project_category=="R&D center" else "No",
            "Yes" if project_category=="Corporate headquarters" else "No",
            "TBD",
            "TBD",
            "TBD",
            "Yes" if irs_sector=="Data processing, hosting, and related services" else "No"
        ]
        ## for inheritance
        self.requirement_array_bol=requirement_array_bol
        requirement_bol="Yes" if requirement_array_bol.count("Yes")>0 else "No"

        ## benefit

        average_ratio=[i/j for i,j in zip(research_and_development,sales)]
        uselesser=[i*min([k,0.3]) for i,k in zip(sales,average_ratio)]
        benefit_10=[i*0.1 for i in uselesser]

        ## credit calculation
        company_ga_sales=[i*state_corporate_income_tax_rate for i in sales]

        rate=[]
        for i in range(10):
            if i <3:
                rate.append(0.3)
            else:

               val=min([(sum(research_and_development[i-3:i])/sum(company_ga_sales[i-3:i])),0.3])
               rate.append(val)


        base_amount=[i*j for i,j in zip(rate,company_ga_sales)]
        excess=[i-j for i,j in zip(research_and_development,base_amount)]
        multiply_benefit=[i*0.1 if i*0.1>0 else 0 for i in excess]
        multiply_benefit.insert(0,0)
        for i in range(11):
            df_dict["year"].append(i)
        self.main_bol="Yes" if requirement_bol.count("Yes")>0 else "No"
        if self.main_bol=="Yes":

            df_dict["value"]=multiply_benefit
        else:
            df_dict["value"]=[0 for i in range(11)]


        return df_dict