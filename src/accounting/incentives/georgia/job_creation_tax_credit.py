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
        year = 5
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
        ### necessary variables
        promised_wage=self.project_level_inputs["Promised wages"]
        geographic_tier=self.sub_class.geographic_teir
        promised_job=self.project_level_inputs["Promised jobs"]

        df_dict=defaultdict(list)

        ## requirement
        ## we need to fix this later, this is in another tab we can call later
        ## right now it is default for sector requirement_bol fix it later
        bol_array=[
            "Yes" if self.project_level_inputs["High-level category"]=="Manufacturing" else "No",
            "Yes" if self.project_level_inputs["Project category"]=="Distribution center" else "No",
            "Yes" if self.project_level_inputs["Project category"]=="Call Center" else "No",
            "Yes" if self.project_level_inputs["Project category"]=="R&D center" else "No",
            "Yes" if self.project_level_inputs["Project category"]=="Corporate headquarters" else "No",
            "TBD",
            "TBD",
            "TBD",
            "Yes" if self.project_level_inputs["IRS Sector"]=="Data processing, hosting, and related services" else "No"
        ]
        sector_requirement_bol="Yes" if bol_array.count("Yes")>0 else "No"

        miscellaneous_requirements="Yes"
        ## this 18696 is default for now but it shoud be look up  in list of special localities

        minimum_wage_requirements="Yes" if promised_wage>=18696 else "No"
        requirement_bol_array=[minimum_wage_requirements,sector_requirement_bol,miscellaneous_requirements]
        requirement_bol="Yes" if requirement_bol_array.count("Yes")==3 else "No"
        requirement_val=None
        #this array value is default for now but need to fix in the tab
        array_lookup=["Tier 1","Tier 2","Tier 3","Tier 4","MZ/OZ","LDCT"]


        array_val=[4000 if self.project_level_inputs["Promised jobs"]>=2 else 0,
                   3000 if self.project_level_inputs["Promised jobs"]>=10 else 0,
                   1750 if self.project_level_inputs["Promised jobs"]>=15 else 0,
                   1250 if self.project_level_inputs["Promised jobs"]>=25 else 0,
                   3500 if self.project_level_inputs["Promised jobs"]>=2 else 0,
                   3500 if self.project_level_inputs["Promised jobs"]>=5 else 0]
        if requirement_bol=="Yes":
            requirement_val=look_up(geographic_tier,array_lookup,array_val)
        elif requirement_bol=="No":
            requirement_val=0

        for i in range(11):
            df_dict["Year"].append(i)
            if requirement_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["Can apply to share of tax liability based on tier"].append(0)
                else:
                    df_dict["Can apply to share of tax liability based on tier"].append(promised_job*requirement_val)
        sum_val1=sum(df_dict["Can apply to share of tax liability based on tier"])
        sum_val2=sum(self.sub_class.sub_array)
        use="Use QJTC" if sum_val2>sum_val1 else "Use JCTC"
        if use=="Use QJTC":
            main_array=[0 for i in range(11)]
        else:
            main_array=df_dict["Can apply to share of tax liability based on tier"]
        df_dict["value"]=main_array
        self.main_bol=requirement_bol

        return df_dict






