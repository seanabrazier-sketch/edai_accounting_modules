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
       attraction=self.project_level_inputs["Attraction or Expansion?"]
       promised_job=self.project_level_inputs["Promised jobs"]
       promised_capital=self.project_level_inputs["Promised capital investment"]

       ## meets requirement

       array_lookup=["Des Moines County",
                     "Pottawattamie County",
                     "Lee County",
                     "Woodbury County"
                     ]
       array_value=[
           21.61,
           22.13,
           22.99,
           21.31
       ]
       value_lookup=None

       value_lookup=look_up(self.county,array_lookup,array_value)


       ## there is an error in rows 1961 where condition is wrong
       first_requirement_array=[
           "No" if value_lookup =="Error" else ("Yes" if promised_job>=value_lookup else "No"),
            "Yes" if promised_job>=10 else "No",
           "Yes" if promised_capital>=500000 else "No"
       ]
       or_bol="Yes" if (first_requirement_array[1]=="Yes" or first_requirement_array[2]=="Yes") else "No"

       second_requirement_array=[
           "Yes" if(attraction=="Relocation" and first_requirement_array[0]=="Yes") else "No",
           "Yes" if (attraction=="Expansion" and first_requirement_array[0]=="Yes" and or_bol=="Yes") else "No"

       ]
       requirement_bol="Yes" if second_requirement_array.count("Yes")==2 else "No"


       ## geographic requiremtns
       geographic_bol=None
       index=None
       try:
          index=array_lookup.index(self.county)
       except:
          index=-1
       if index==-1:
           geographic_bol=="No"
       elif index>=0:
           geographic_bol=="Yes"


       #requirement_local
       require_local_participation_bol="Yes" if (geographic_bol=="Yes" and requirement_bol=="Yes")  else "No"
       require_local_array=[]
       promised_wage=self.project_level_inputs["Promised wages"]
       for i in range(11):
           if require_local_participation_bol=="No":
               require_local_array.append(0)
           else:
               ## there is an error on excel through this row
               require_local_array.append(promised_wage*promised_job*0.03)

       require_local_array.insert(0,0)

       year=[i for i in range(11)]
       df_dict=defaultdict(list)
       df_dict["year"]=year
       df_dict["value"]=require_local_array
       self.main_bol=require_local_participation_bol

       return df_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Iowa")
                value = i.replace("Iowa", "IA")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", IA")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county
