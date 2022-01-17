from accounting.incentives import *
import pandas
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from util.npv import npv
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self,**kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.capex = kwargs['capex']
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.other_requirements_info = self.other_requirements()
        self.all_input=kwargs
        self.pnl_input=kwargs['pnl_inputs']

        self.minimum_capex_info=self.minimum_capex()
        self.get_zone_info=self.get_zone()
        self.minimum_wage_info=self.minimum_wages()

        self.county=self.get_county_name()
        self.project_benefit_df_info = self.project_benefit_df()
        self.final_return_info=self.final_return()

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
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
    def project_benefit_df(self):
        bol="Yes" if (self.other_requirements_info["bol"]=="Yes" and self.minimum_wage_info["bol"]=="Yes" and self.minimum_capex_info["bol"]=="Yes" and self.other_requirements_info["Meaning, manufacturing + any of the four criteria"]=="Yes") else "No"
        promised_jobs=self.project_level_inputs["Promised jobs"]
        array1=[self.other_requirements_info["bol"],self.minimum_wage_info["bol"],self.minimum_capex_info["bol"],self.other_requirements_info["Meaning, manufacturing + any of the four criteria"]]
        # print(array1)
        data={
            "Total qualified investment":[0.1],
              "Per qualified job":[20000],
              "Per project":[30000000]
              }
        df = pandas.DataFrame(data)
        array=[]
        if bol == "No":

            for i in range(0,2):
                array.append(0)
        else:
            array.append(0.1*self.minimum_capex_info["Qualified capex"])
            array.append(promised_jobs*20000)
            array.append(30000000)
        json_return={
            "project_benefits_lesser":array,
            "bol":bol
        }
        return json_return
    def final_return(self):
        array_val=self.project_benefit_df_info["project_benefits_lesser"]
        minimum_val=min(array_val)
        df_dict=defaultdict(list)
        project_benefit_bol=self.project_benefit_df_info["bol"]
        year = 1
        for i in range(year+1):
            df_dict["year"].append(i)
            if project_benefit_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(minimum_val)
        self.main_bol=project_benefit_bol

        return df_dict

    def minimum_capex(self):
        Construction_material_value = self.capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,
                                                        industry_type=IndustryType.INDUSTRIAL)
        real_property_land=self.capex.amount(property_type=RealProperty.LAND,industry_type=IndustryType.INDUSTRIAL)
        machinery_and_equipment=self.capex.amount(property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT,industry_type=IndustryType.INDUSTRIAL)
        fixtures=self.capex.amount(property_type=PersonalProperty.FIXTURES,industry_type=IndustryType.INDUSTRIAL)

        sum_value=Construction_material_value+real_property_land+machinery_and_equipment+fixtures

        json_return={"Qualified capex":sum_value,
              "Assumes at least 80% of property and payroll dedicated to sector activity":"",
              "bol":"Yes" if sum_value >250000 else "No"
              }

        return json_return
    def minimum_wages(self):
        promised_wage=self.project_level_inputs['Promised wages']
        json_return={}
        json_return["At least 51% of jobs at or above median"]="Yes" if promised_wage>=1.25*self.project_level_inputs['Prevailing wages']["Arizona"] else "No"
        json_return["Rural area?"]="Yes" if self.zone_type_1=="Rural" else "No"
        json_return["Rural areas:"]="Yes" if (json_return["Rural area?"]=="Yes" and promised_wage>=self.project_level_inputs['Prevailing wages']["Arizona"]) else "No"
        json_return["bol"]="Yes" if (json_return["At least 51% of jobs at or above median"]=="Yes" or json_return['Rural area?']=="Yes") else "No"

        return json_return

    def get_zone(self):
        try:
            self.zone_type_1=self.zone_type_1[self.county]
        except:
            self.zone_type_1="-"
    def get_county_name(self):
        county=[]
        county_list=self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index=i.index(", AZ")
                county.append(i)
                break
            except:
                pass

        if len(county)>0:
            county=county[0]
        else:
            county
        return county
    def other_requirements(self):
        json_return={}
        # print(self.project_level_inputs["Rollup IRS sector"])
        json_return["Labor-intensive manufacturer"]="Yes" if self.project_level_inputs["Rollup IRS sector"]=="Labor-intensive manufacturer" else "No"
        json_return["Capital-intensive manufacturer"]="Yes" if self.project_level_inputs["Rollup IRS sector"]=="Capital-intensive manufacturer" else "No"
        json_return["R&D Center"]="Yes" if self.project_level_inputs["Rollup IRS sector"]=="R&D Center" else "No"
        json_return["Corporate Headquarters"]="Yes" if self.project_level_inputs["Rollup IRS sector"]=="Corporate Headquarters" else "No"
        json_return["Manufacturing total"]="Yes" if self.project_level_inputs["Rollup IRS sector"]=="Manufacturing total" else "No"
        json_return["bol"]="Yes"
        ## an error here occur in the excel sheet
        ## in the excel sheet it says Manufacturing but in reality it is manufacturing total
        ## this is right need to fix this it is not roll oi[ irs G8 is Hig-level category

        array_count=[json_return[i] for i in json_return if i!="Manufacturing total"]
        count_yes=array_count.count("Yes")
        json_return["Meaning, manufacturing + any of the four criteria"]="Yes" if (json_return["Manufacturing total"]=="Yes" and count_yes>0) else "No"

        return json_return



