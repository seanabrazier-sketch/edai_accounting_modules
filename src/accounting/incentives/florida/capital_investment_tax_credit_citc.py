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
        ## necessary variab;es
        promised_capital=self.project_level_inputs["Promised capital investment"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        high_impact_array=self.sub_class.high_impact_array
        #credit to use tab
        capex_range=[0,25000000,50000000,100000000]
        credit=[0,0.5,0.75,1]
        credit_to_use_val=v_lookup_2(promised_capital,capex_range,credit)

        ## requirement
        requirement_array=["Yes" if promised_jobs>=100 else "No",
                           "Yes" if promised_capital>=25000000 else "No",
                           "Yes" if high_impact_array.count("Yes")>0 else "No",
                        ]

        ## main tab
        main_bol="Yes" if requirement_array.count("Yes")==3 else "No"
        ## benefit array
        default_rate=0.05
        benefit_array=[]
        df_dict=defaultdict(list)
        for i in range(11):
            df_dict["year"].append(i)
            if main_bol=="No":
                benefit_array.append(0)
            else:
                if i==0:
                    benefit_array.append(0)
                else:
                    benefit_array.append(0.05 * promised_capital)
        df_dict["value"]=benefit_array
        self.main_bol=main_bol

        return df_dict

