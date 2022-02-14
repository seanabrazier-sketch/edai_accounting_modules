from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *
from accounting.incentives.georgia.quality_jobs_tax_credit import IncentiveProgram as subclass
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

        geographic_teir=self.sub_class.geographic_teir
        promised_capital=self.project_level_inputs["Promised capital investment"]
        attraction_expansion=self.project_level_inputs["Attraction or Expansion?"]
        array_lookup=["Tier 1","Tier 2","Tier 3","Tier 4"]
        df_dict=defaultdict(list)
        land=self.capex.amount(property_type=RealProperty.LAND,industry_type=self.pnl_input["industry_type"])
        construction=self.capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,industry_type=self.pnl_input["industry_type"])
        construction_labor=self.capex.amount(property_type=RealProperty.CONSTRUCTION_LABOR,industry_type=self.pnl_input["industry_type"])
        sum_val=land+construction+construction_labor

        ## the array value for now is default need to fix it later

        array_value=[0.05 if promised_capital>=100000 else 0,
                     0.03 if promised_capital>=100000 else 0,
                     0.01 if promised_capital>=100000 else 0,
                     0.01 if promised_capital>=100000 else 0]
        ## requirement
        requirement_bol="Yes" if attraction_expansion=="Expansion" else "No"


        #main tab
        main_bol=requirement_bol
        rate_to_use=look_up(geographic_teir,array_lookup,array_value)

        for i in range(11):
            df_dict["year"].append(i)
            if main_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(min[1000000,rate_to_use*sum_val])
        self.main_bol=main_bol

        return df_dict




