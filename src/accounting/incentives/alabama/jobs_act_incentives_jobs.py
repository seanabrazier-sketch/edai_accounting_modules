from accounting.incentives import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from util.npv import npv
from accounting.data_store import *
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self,**kwargs):

        self.all_input=kwargs
        self.project_level_inputs = kwargs['project_level_inputs']

        self.capex=kwargs['capex']
        self.county=self.get_county_name()
        self.get_zone = self.get_zone()
        self.technology_company_qualification_info = self.technology_company_qualification()
        self.cash_rebate_benefit_info = self.cash_rebate_benefit()
        self.job_creation_thresholds_info=self.job_creation_thresholds()
        self.capital_investment_thresholds_info=self.capital_investment_thresholds()
        self.requirement_info=self.requirement()
        self.total_benefit_to_use_info=self.total_benefit_to_use()
        self.final_return_info=self.total_benefit_to_use_info
    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
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

                    if k > year:
                        array_value.append(0)
                    else:

                        array_value.append(final_value[i][k])

                value = excel_npv(self.discount_rate, final_value[i][start_year:year+1 + start_year])
                final_value[i] = array_value
                npv_value.append(value)

        final_value["NPV_Name"] = string_name
        final_value["NPV_Value"] = npv_value

        return final_value

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Alabama")
                value = i.replace("Alabama", "AL")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", AL")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

    def get_zone(self):

        try:
            zone_type_1 = list_of_special_localities()["Zone Type 1"]
            self.zone_type_1 = zone_type_1[self.county]
            if len(self.zone_type_1) == 0:
                self.zone_type_1 = "-"
        except:
            self.zone_type_1 = "-"
        try:
            zone_type_2 = list_of_special_localities()["Zone Type 2"]
            self.zone_type_2 = zone_type_2[self.county]
            if len(self.zone_type_2) == 0:
                self.zone_type_2 = "-"
        except:
            self.zone_type_2 = "-"
        try:
            zone_type_3 = list_of_special_localities()["Zone Type 3"]
            self.zone_type_3 = zone_type_3[self.county]
            if len(self.zone_type_3) == 0:
                self.zone_type_3 = "-"

        except:
            self.zone_type_3 = "-"
    def locating_in_target_or_jumpstart_county(self):
        count_list=[self.zone_type_1,self.zone_type_2,self.zone_type_3]

        count_targeted=count_list.count("*Target*")

        count_jumpstart=count_list.count("*Jumpstart")
        return_val=""
        if (count_targeted>0) or (count_jumpstart>0):
            return_val="Yes"
        else:
            return_val="No"

        return return_val
    #this is correct

    def technology_company_qualification(self):
        project_category=self.project_level_inputs['Project category']
        json_return={
            'AL will be corporate HQ': "Yes" if project_category=="Corporate Headquarters" else "No",
            'AL will become residence for top 3 excecs': "Yes",
            'AL will be residence for at least 75% of employees': "Yes",
            'At least 75% of revenue from specific codes': "Yes" if self.project_level_inputs['High-level category']=="Information" else "No"
        }
        array_count=[json_return[i] for i in json_return]
        count=array_count.count("Yes")
        json_return['Technology company qualifications']="Yes" if count==4 else "No"

        return json_return
    # this is good

    def cash_rebate_benefit(self):
        json_return={
            "Previous year's gross payroll":("Yes",0.03),
            "Wages for veterans":("n/a",0.005),
            'Locating in Targeted or Jumpstart County':(self.locating_in_target_or_jumpstart_county(),0.01),
            'Locating within former active duty military use':("n/a",0.005),
            'Technology companies, up to 2%': (self.technology_company_qualification_info['Technology company qualifications'],0.02)
        }

        return json_return
    #this is now correct and checked

    def job_creation_thresholds(self):

        json_return={
            "Non-targeted/non-jumpstart county":{
                "Category": "No" if self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="Yes" else "Yes",
                "Meets min jobs?": "Yes" if(self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="No" and self.project_level_inputs['Promised jobs']>=50) else "No"
            },
            "Targeted Jumpstart County":{
               "Category":self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0],
                "Meets min jobs?": "Yes" if (self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="Yes" and self.project_level_inputs['Promised jobs']>10) else "No"
            },
            "Technology company":{
                "Category":self.cash_rebate_benefit_info['Technology companies, up to 2%'][0],
                "Meets min jobs?":"Yes" if (self.cash_rebate_benefit_info['Technology companies, up to 2%'][0]=="Yes" and self.project_level_inputs['Promised jobs']>5) else "No"

            },
            # inform Sean about this
            # there is no value for this to check with

            "Miscellaneous":{
                "Category":"n/a",
                "Meets min jobs?": "No"
            },
            "Data Center":{
                "Category":"Yes" if self.project_level_inputs['IRS Sector']=="Data processing, hosting, and related services" else "No",
                "Meets min jobs?":"Yes" if (self.project_level_inputs['IRS Sector']=="Data processing, hosting, and related services" and self.project_level_inputs["Promised jobs"]>1) else "No"
            },
            "R&D Center":
                {
                    "Category": "Yes" if self.project_level_inputs['Project category']=="R&D Center" else "No",
                    "Meets min jobs?":"Yes" if (self.project_level_inputs['Project category']=="R&D Center" and self.project_level_inputs["Promised jobs"]>1) else "No"
                }
        }

        return json_return

    def capital_investment_thresholds(self):
        Construction_material_value=self.capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,industry_type=IndustryType.INDUSTRIAL)
        Personal_Machinary_Equipment=self.capex.amount(property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT,industry_type=IndustryType.INDUSTRIAL)
        sum=Construction_material_value+Personal_Machinary_Equipment

        json_return={
            "Non-targeted/non-jumpstart county":{
                "Category":"No" if self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="Yes" else "Yes",
                "Meets min":"Yes" if (sum>=0 and self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="No") else "No"
            },
            "Targeted or Jumpstart county":{
                "Category":"Yes" if self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="Yes" else "No",
                "Meets min":"Yes" if (self.cash_rebate_benefit_info['Locating in Targeted or Jumpstart County'][0]=="Yes" and sum>=2000000) else "No",
            }
        }

        return json_return
    # this is check and correct

    def requirement(self):
        count_minimum_jobs = [self.job_creation_thresholds_info[i]["Meets min jobs?"] for i in
                              self.job_creation_thresholds_info]
        count_minimum_capital = [self.capital_investment_thresholds_info[i]["Meets min"] for i in self.capital_investment_thresholds_info]

        count_minimum_jobs_val=count_minimum_jobs.count("Yes")
        count_minimum_capital_val=count_minimum_capital.count("Yes")
        json_return = {
            "Minimum jobs": "Yes" if count_minimum_jobs_val>0 else "No",
            "Minimum capital investment":"Yes" if count_minimum_capital_val>0 else "No"

        }

        return json_return

    def total_benefit_to_use(self):
        cash_rebate=self.cash_rebate_benefit_info
        total_benefit_bol="Yes" if (self.requirement_info["Minimum jobs"]=="Yes" and self.requirement_info["Minimum capital investment"]=="Yes") else "No"
        year=10
        cash_rebate_rate=[cash_rebate[i][1] for i in cash_rebate if cash_rebate[i][0]=="Yes"]
        cash_rebate_rate_sum=sum(cash_rebate_rate)

        #create a default dictionary
        payroll = self.project_level_inputs['Equivalent payroll (BASE)']

        total_benefit_info=defaultdict(list)
        for i in range(year+1):
            total_benefit_info["year"].append(i)

            if total_benefit_bol=="No":
                total_benefit_info['value'].append(0)
            else:
                if i ==0:
                    total_benefit_info['value'].append(0)
                else:
                    total_benefit_info['value'].append(float(payroll)*float(cash_rebate_rate_sum))


        self.main_bol=total_benefit_bol

        return total_benefit_info









