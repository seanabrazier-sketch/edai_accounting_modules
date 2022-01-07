from accounting.incentives import *
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
class IncentiveProgram(IncentiveProgramBase):
    # this class is inherited from the init class of incentives

    def __init__(self,**kwargs):
        self.sub_class=jobs(**kwargs)
        self.project_level_inputs=kwargs['project_level_inputs']
        self.qualifying_project_info=self.qualifying_project()
        self.requirement_info=self.requirement()
        self.benefit_info=self.benefit()
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
    def qualifying_project(self):
        json_return={
            "Distribution center":2000000,
            "R&D Center":2000000,
            "Capital-intensive manufacturer":2000000,
            "Labor-intensive manufacturer":2000000,
            "Corporate manufacturer":2000000
        }
        return json_return
    def requirement(self):
        json_return={
            "Qualified project": "Yes" if self.project_level_inputs["Promised capital investment"]>=2000000 else "No",
            "Technology company":self.sub_class.technology_company_qualification_info['At least 75% of revenue from specific codes'],
            "Ineligile because receiving Jobs Act Jobs credits?":"No" if self.sub_class.total_benefit_to_use_info["bol"]=="No" else "Yes",
            "Locating in Targeted or Jumpstart County":self.sub_class.locating_in_target_or_jumpstart_county(),
            "Can be applied against state income tax and few others":""

        }
        count_array=[json_return[i] for i in json_return if json_return[i]=="Yes"]
        count_yes=count_array.count("Yes")
        json_return["Requirements"]="Yes" if count_yes==3 else "No"
        return json_return
    def benefit(self):
        json_return={
            "Qualified capital investment":"Yes",
            "Assumes full capex figure":0.015
        }
        return json_return
    def final_return(self):

            year=15 if self.requirement_info['Locating in Targeted or Jumpstart County']=="Yes" else 10
            def_dict=defaultdict(list)
            for i in range(year+1):
                def_dict["year"].append(i)
                if self.requirement_info["Requirements"]=="No":
                    def_dict["value"].append(0)
                else:
                    if i==0:
                        def_dict["year"].append(0)
                    else:
                        def_dict["value"].append(self.project_level_inputs["Promised capital investment"]*self.benefit_info["Assumes full capex figure"])

            self.main_bol=self.requirement_info["Requirements"]
            return def_dict





