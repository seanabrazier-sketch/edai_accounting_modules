from accounting.incentives import *
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sector_info=self.sector()
        self.capex = kwargs['capex']
        self.data_center_info=self.data_center()
        self.pnl_input=kwargs["pnl_inputs"]
        self.requirement_info=self.requirement()
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

    def sector(self):
        json_return={
            "All sectors":("Yes","Yes"),# get this from state specific sector, # this need to check with Sean about the information on the excel formula, now it will be hard coded


            "Corporate headquarters":("Yes" if self.project_level_inputs["Project category"]=="Corporate headquarters" else "No","Yes" if (self.project_level_inputs["Project category"]=="Corporate headquarters" and self.project_level_inputs["Promised jobs"]>50) else "No"),
            "Data processing, hosting, and related services": ("Yes" if self.project_level_inputs["IRS Sector"]=="Data processing, hosting, and related services" else "No","Yes" if (self.project_level_inputs["IRS Sector"]=="Data processing, hosting, and related services" and self.project_level_inputs["Promised jobs"]>20 and self.project_level_inputs["Promised wages"]>40000) else "No")

        }
        return json_return

    def requirement(self):
        Construction_material_value = self.capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,
                                                        industry_type=IndustryType.INDUSTRIAL)
        Personal_Machinary_Equipment = self.capex.amount(property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT,
                                                         industry_type=IndustryType.INDUSTRIAL)
        sum=Construction_material_value+Personal_Machinary_Equipment
        json_return = {
            "In qualifying sector or activity": "No",  # this will need to get check with Sean as well since we are going to work on excel sheet
            "Minimum jobs based on table": self.sector_info['Data processing, hosting, and related services'][1] if self.sector_info['Data processing, hosting, and related services'][0]=="Yes" else (self.sector_info["Corporate headquarters"][1] if self.sector_info["Corporate headquarters"][0]=="Yes" else self.sector_info["All sectors"][1]),
            "New project": "No" if self.project_level_inputs['Attraction or Expansion?']=="Expansion" else "Yes",
            "Expansion (lesser of the two)": "Yes" if sum >=2000000 else "No"
        }
        json_return["sum"]=sum

        count_array=[json_return["New project"],json_return["Expansion (lesser of the two)"]]
        count=count_array.count("Yes")
        json_return["Minimum capital investment"]="Yes" if count >0 else "No"
        return json_return
    def data_center(self):
        json_return={
            # there is another error in the excel sheet look for data center in the tax exemptions

            "Sector requirement":"Yes" if self.project_level_inputs['IRS Sector']=="Data processing, hosting, and related services" else "No",
            "Minimum capex":["Yes" if self.project_level_inputs["Promised capital investment"]>=0 else "No","Yes" if self.project_level_inputs["Promised capital investment"]>=200000000 else "No", "Yes" if self.project_level_inputs["Promised capital investment"]>=200000000 else "No"]

        }
        ## lookup we want to find the smallest value we can use variance in this case
        year=[10,20,30]
        lookup=lambda x: [(x-0)**2,(x-200000000)**2,(x-400000000)**2]
        array=lookup(self.project_level_inputs["Promised capital investment"])
        min_val=min(array)
        index=array.index(min_val)
        year_choose=year[index]
        count_yes=json_return["Minimum capex"].count("Yes")
        json_return["Data center"]=("Yes" if (json_return["Sector requirement"]=="Yes" and count_yes>0) else "No",year_choose)
        return json_return
    def final_return(self):
        df_dict=defaultdict(list)
        year=10
        for i in range(year+1):
            df_dict["year"].append(i)
            if self.data_center_info["Data center"][0]=="No":
                df_dict["value"].append(0)
            else:
                if i ==0:
                    # this tax has an optional state as well

                    df_dict["value"].append(self.pnl_input["state_local_sales_tax_rate"]*(self.requirement_info["sum"]))
                else:
                    df_dict["value"].append(self.pnl_input["state_local_sales_tax_rate"]*self.npv_dicts['Annual capital expenditures option 2'][i])
        self.main_bol=self.data_center_info["Data center"][0]

        return df_dict



