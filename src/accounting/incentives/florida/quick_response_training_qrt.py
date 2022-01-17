from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *
from accounting.incentives.florida.qualified_target_industry_tax_refund_qti import IncentiveProgram as subclass
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sub_class=subclass(**kwargs)
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
        promised_job=self.project_level_inputs["Promised jobs"]
        high_level_category=self.project_level_inputs["High-level category"]
        project_category=self.project_level_inputs["Project category"]
        promised_wage= self.project_level_inputs["Promised wages"]
        df_dict=defaultdict(list)
        ## eligible array
        eligible_array_bol=[
            "Yes" if high_level_category=="Manufacturing" else "No",
            "Yes" if project_category=="Corporate headquarters" else "No",
            "Yes" if project_category=="R&D center" else "No",
            "n/a",
            "n/a",
            "Yes" if high_level_category=="Information" else "No",
            "n/a",
            "n/a",
            "Yes" if high_level_category=="Finance and insurance" else "No"
        ]
        county_prevailing_wages=self.sub_class.prevailing_wages
        state_prevailing_wages=self.project_level_inputs["Prevailing wages"]["Florida"]
        ## main tab
        min_prevailing_wages=min(county_prevailing_wages,state_prevailing_wages)
        main_array_bol=[
            "Yes" if promised_wage>=min_prevailing_wages*1.25 else "No",
            "Yes" if promised_wage>=county_prevailing_wages*1.25 else "No",
            "Yes" if promised_wage >= state_prevailing_wages * 1.25 else "No",
            "Yes"
        ]
        main_bol="Yes" if (main_array_bol[0]=="Yes" and main_array_bol[-1]=="Yes") else "No"

        ## grant estimates mics sources has not been integrated, fixed this later for default vlaue
        default_value=grant_estimates_misc_2_df["Average Cost per trainee"]["Florida Quick Response Training"]


        for i in range(2):
            df_dict["Year"].append(i)
            if main_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(promised_job*default_value)
        self.main_bol=main_bol

        return df_dict