from accounting.incentives import *
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.details_info=self.details()
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
        year = 10
        final_value = self.final_return_info
        npv_value = []
        string_name = []
        start_year = 1

        for i in self.final_return_info:
            if i != "year" and i != "Year":
                array_value=[]

                string = "npv_{}".format(i)
                string_name.append(string)
                for k in range(11):
                    if k<start_year:
                        array_value.append("Base")
                        continue

                    if k>year:
                        array_value.append(0)
                    else:

                        array_value.append(final_value[i][k])

                value = excel_npv(self.discount_rate, final_value[i][start_year:year + start_year])
                final_value[i] = array_value
                npv_value.append(value)

        year_list = [i for i in range(year)]
        final_value["year"] = year_list
        final_value["NPV_Name"] = string_name
        final_value["NPV_Value"] = npv_value

        return final_value
    def details(self):
        project_category=self.project_level_inputs["Project category"]
        json_return={
            "In qualifying sector":"Yes", # this is from state_specific_sector and need to be fixed later after Sean added in
            "Or qualifying activity":"Yes" if(project_category=="Corporate Headquarters" or project_category=="R&D Center") else "No",
            "Up to $200M":"",
            "$200-$400M":"",
            "Over $400M":"",

        }
        json_return["bol"]="Yes" if (json_return['In qualifying sector']=="Yes" or json_return["Or qualifying activity"]=="Yes") else "No"
        return json_return
    def final_return(self):
        promised_capital=self.project_level_inputs['Promised capital investment']
        money=[0,200000000,400000000]
        var=[(promised_capital-i)**2 for i in money]
        min_var=min(var)
        index_look=var.index(min_var)
        year=[10,20,30]
        year_choose=year[index_look]
        bol="Yes"
        percentage=1
        detail_bol=self.details_info["bol"]
        def_dict=defaultdict(list)
        property_tax=self.npv_dicts['Property tax'][1]

        for i in range(year_choose+1):
            def_dict['year'].append(i)
            if i==0:
                def_dict['value'].append("-")
            else:
                if detail_bol=="Yes":
                    def_dict['value'].append(float(property_tax)*percentage)

                else:
                    def_dict['value'].append(0)
        self.main_bol=bol

        return def_dict



