from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

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
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
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

    def final_return(self):
        #necessary_variable
        irs_sector=self.project_level_inputs["IRS Sector"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        promised_capital=self.project_level_inputs["Promised capital investment"]
        promised_wage=self.project_level_inputs["Promised wages"]
        anual_expenditure=self.npv_dicts["Annual capital expenditures option 2"]
        construction=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=RealProperty.CONSTRUCTION_MATERIAL)
        machinery=self.capex.amount(industry_type=self.pnl_input["industry_type"],property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        sum_value=construction+machinery
        state_local_sales_tax=self.pnl_input["state_local_sales_tax_rate"]
        first_val=state_local_sales_tax*sum_value
        ## requirement
        requirement_bol_array=[
            "Yes" if irs_sector=="Data processing, hosting, and related services" else "No",
            "Yes" if promised_jobs>=30 else "No",
            "Yes" if promised_capital>=250000000 else "No",
            "Yes" if promised_wage>=42240 else "No"
        ]
        #main_tab
        main_bol="Yes" if requirement_bol_array.count("Yes")==4 else "No"
        self.main_bol=main_bol
        main_array=[]
        for i in range(11):
            if main_bol=="Yes":
                if i ==0:
                    main_array.append(first_val)
                else:
                    main_array.append(anual_expenditure[i]*state_local_sales_tax)
            else:
                main_array.append(0)
        year=[i for i in range(11)]
        df_dict=defaultdict(list)
        df_dict["year"]=year
        df_dict["value"]=main_array
        return df_dict
