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
        #necessary variable
        promised_jobs=self.project_level_inputs["Promised jobs"]
        promised_capital=self.project_level_inputs["Promised capital investment"]
        promised_wage=self.project_level_inputs["Promised wages"]
        federal_minimum=self.project_level_inputs["Federal minimum wage"]
        ## requiremnt Standard
        requirement_bol_array=[
            "Yes" if promised_jobs>=10   else "No",
            "Yes" if promised_capital>=100000 else "No",
            "Yes" if promised_wage>=federal_minimum*2080*1.5 else "No",
            "Yes"
        ]
        requirement_bol="Yes" if requirement_bol_array.count("Yes")==4 else "No"

        ## requirement_enhance

        requirement_enhance_array=[
            "Yes" if promised_jobs>=10 else "No",
            "Yes" if promised_capital>=100000 else "No",
            "Yes" if federal_minimum*2080*1.25 else "No",
            "Yes"
        ]

        requirement_enhance_bol="Yes" if requirement_enhance_array.count("Yes")==4 else "No"
        #main requirment
        high_level=self.project_level_inputs["High-level category"]
        project_category=self.project_level_inputs["Project category"]
        main_requirement_array=[
            "Yes" if high_level=="Manufacturing" else "No",
            "Yes" if high_level=="R&D Center" else "No",
            "Yes" if project_category=="Corporate headquarters" else "No",
        ]

        main_requirement_bol="Yes" if main_requirement_array.count("Yes")>0 else "No"

        #standard incentive
        standard_bol='Yes' if requirement_bol=="Yes" and main_requirement_bol=="Yes" else "No"

        #benefit
        benefit_bol="Yes" if main_requirement_bol=="Yes" and requirement_enhance_bol=="Yes" else "No"

        #main tab
        main_bol="Yes" if standard_bol=="Yes" or benefit_bol=="Yes" else "No"

        standard_incentive_1=[]
        standard_incentive_2=[]
        benefit_1=[]
        benefit_2=[]
        main_array=[]
        year=[]
        state_income_tax=self.npv_dicts["State corporate income tax"]
        for i in range(11):
            year.append(i)
            if i==0:
                standard_incentive_1.append(0)
                standard_incentive_2.append(0)
                benefit_2.append(0)
                benefit_1.append(0)
                main_array.append(0)
                continue
            else:
                if standard_bol=="Yes":
                    standard_incentive_1.append(0.04*promised_wage*promised_jobs)
                    standard_incentive_2.append(state_income_tax[i])
                else:
                    standard_incentive_1.append(0)
                    standard_incentive_2.append(0)
                if benefit_bol=="Yes":
                    benefit_1.append(promised_jobs*promised_wage*0.05)
                    benefit_2.append(state_income_tax[i])
                else:
                    benefit_1.append(0)
                    benefit_2.append(0)
                if main_bol=="Yes":

                    if benefit_bol=="Yes":
                        main_array.append(benefit_1[-1]+benefit_2[-1])

                    else:
                        if standard_bol=="Yes":
                            main_array.append(standard_incentive_1[-1]+standard_incentive_2[-1])
                else:
                    main_array.append(0)
        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        self.main_bol=main_bol
        return  df_dict
