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
        self.all_input=kwargs

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
        year = 1
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
        median=self.all_input['discretionary_incentives_groups'].median()
        median_val=median["Incentive per job"]["Arizona Competes Fund"]

        #g14
        #High-level category G8
        #Promised wages 14
        #G9 Project category
        promised_wage=self.project_level_inputs['Promised wages']
        high_level_category=self.project_level_inputs["High-level category"]
        project_category=self.project_level_inputs["Project category"]
        array=["Yes" if high_level_category=="Manufacturing" else "No","Yes" if project_category=="R&D Center" else "No", "Yes" if project_category=="Corporate headquarters" else "No","Yes" if project_category=="Distribution center" else "No","No"]
        count_yes=array.count("Yes")
        sector_is_industry="Yes" if count_yes>0 else "No"
        require_health_insurance="Yes"
        county_wages="Yes" if promised_wage>=57356 else "No"
        array_count=[sector_is_industry,require_health_insurance,county_wages]
        array_count_yes=array_count.count("Yes")
        bol="Yes" if  array_count_yes ==3 else "No"
        df_dict=defaultdict(list)
        year=1
        promised_jobs=self.project_level_inputs["Promised jobs"]
        for i in range(year+1):
            df_dict["year"].append(i)
            if bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(promised_jobs*median_val)
        self.main_bol=bol

        return df_dict
