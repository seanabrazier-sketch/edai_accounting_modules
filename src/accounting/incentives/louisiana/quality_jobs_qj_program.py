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

        self.pnl_input=kwargs["pnl_inputs"]
        self.county=self.get_county_name()
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
        #requirement
        promised_job=self.project_level_inputs["Promised jobs"]
        payroll=self.project_level_inputs["Equivalent payroll (BASE)"]

        meet_requirement_array=[
            "Yes" if promised_job>=5 and payroll>=225000 else "No",
            "Yes" if promised_job>=15 and payroll>=675000 else "No",

        ]
        requirement_bol_array=[
            "Yes" if meet_requirement_array.count("Yes")>0 else "No",
            "Yes"
        ]
        requirement_bol="Yes" if requirement_bol_array.count("Yes")==2 else "No"

        ## eligibility
        project_cat=self.project_level_inputs["Project category"]

        high_level=self.project_level_inputs["High-level category"]
        irs_sector=self.project_level_inputs["IRS Sector"]

        eligibile_sector_array=[
            "Yes" if project_cat=="R&D Center" else "No",
            "Yes" if high_level=="Manufacturing" else "No",
            "Yes" if high_level=="Information" else "No",
            "-",
            "Yes" if irs_sector=="Food manufacturing" else "No",
            "-",
            "Yes" if project_cat=="Corporate headquarters" else "No",
            "-",
            "-",
        ]
        percapital_income=None
        if isinstance(self.county,str):
            percapital_income=self.project_level_inputs["county_to_per_capita_income"][self.county]
        else:
            percapital_income=self.all_input["state_to_per_capita_income"]["Louisiana"]
        state_capital=self.all_input["state_to_per_capita_income"]["Louisiana"]

        eligible_bol_array=[
            "Yes" if eligibile_sector_array.count("Yes")>0 else "No",
            "-",
            "-",
            "Yes" if percapital_income<(state_capital*0.25) else "No"
        ]

        eligible_bol="Yes" if eligible_bol_array.count("Yes")>0 else "No"

        promised_wage=self.project_level_inputs["Promised wages"]
        # cash benefit
        cash_benefit_array=[
            "Yes" if ((promised_wage/2080)>18) else "No",
            "Yes" if ((promised_wage/2080)>21.66) else "No",
        ]
        cash_benefit_bol="Yes" if  cash_benefit_array.count("Yes")==2 else "No"


        ## main tab
        main_bol="Yes" if (cash_benefit_bol=="Yes" and eligible_bol=="Yes" and requirement_bol=="Yes") else "No"

        promised_cap=self.project_level_inputs["Promised capital investment"]
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        array1=[]
        array2=[]
        array3=[]
        array4=[]
        main_array=[]
        anual_exp=self.npv_dicts["Annual capital expenditures option 2"]

        state_local_sales_tax=self.pnl_input["state_local_sales_tax_rate"]
        array_value=[0.04,0.06]
        rate_choose=choose_with_condition("max","Yes",cash_benefit_array,array_value)
        for i in range(11):
            if main_bol=="Yes":
                array1.append(payroll*rate_choose)
                array2.append(promised_cap*0.015)
                if i==0:
                    array3.append(state_local_sales_tax*machinery)
                else:
                    array3.append(state_local_sales_tax *anual_exp[i])
            else:
                array1.append(0)
                array2.append(0)
                array3.append(0)
        array1[0]=0
        array2[0]=0

        sum_val2=sum(array2)
        sum_val3=sum(array3)
        max_val=max([sum_val3,sum_val2])
        condition_title="Use sales tax" if max_val==sum_val3 else "Use project facility expense"

        condition_val=2 if condition_title=="Use project facility expense" else 1
        array4=array3 if condition_val==1 else array2

        main_array=[max(i,j) if main_bol=="Yes" else 0 for i,j in zip(array4,array1)]
        main_array[0]=0
        year=[i for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        self.main_bol=main_bol
        return df_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Louisiana")
                value = i.replace("Louisiana", "LA")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", LA")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
