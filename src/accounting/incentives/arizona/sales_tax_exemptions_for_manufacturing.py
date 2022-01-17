from accounting.incentives import *
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex = kwargs['capex']

        self.pnl_input=kwargs["pnl_inputs"]

        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.final_return_info=self.final_return()

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
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
        anual_capital=self.npv_dicts['Annual capital expenditures option 2']
        high_level_category=self.project_level_inputs['High-level category']
        bol1="Yes" if high_level_category=="Manufacturing" else "No"
        bol2="Yes" if high_level_category=="R&D Center" else "No"
        main_bol="Yes" if (bol1=="Yes" or bol2=="Yes") else "No"
        state_local_tax_rate=self.pnl_input["state_local_sales_tax_rate"]
        machinary_equipment=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        df_dict=defaultdict(list)
        year=10
        for i in range(year+1):
            df_dict["year"].append(i)
            if main_bol=="No":

                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(state_local_tax_rate*machinary_equipment)
                else:
                    pass
                    df_dict["value"].append(anual_capital[i]*state_local_tax_rate)
        self.main_bol=main_bol

        return df_dict