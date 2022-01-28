from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *
from util import georgia_config

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
        if self.main_bol == "Yes":
            return True
        else:
            return False
    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year =10
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
        high_level_category=self.project_level_inputs["High-level category"]
        project_category=self.project_level_inputs["Project category"]
        machinery=self.capex.amount(property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT,industry_type=self.pnl_input["industry_type"])
        irs_sector=self.project_level_inputs["IRS Sector"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        real_construction_material = self.capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,
                                      industry_type=self.pnl_input["industry_type"])
        land= self.capex.amount(property_type=RealProperty.LAND,
                                      industry_type=self.pnl_input["industry_type"])
        total_tax_real_prop=real_construction_material+land
        state_local_sales_tax_rate=self.pnl_input["state_local_sales_tax_rate"]
        anual_expenditure=self.npv_dicts["Annual capital expenditures option 2"]
        #county population
        default_amount=0
        ## this population need to inform to Sean

        population_check=["Yes" if default_amount<30001 else "No",
                          "Yes" if default_amount>=50001 else "No",
                          ]
        population_check.insert(1,"Yes" if (population_check[0]=="No" and population_check[-1]=="No") else "No")

        meets_capex=["Yes" if (population_check[0]=="Yes" and total_tax_real_prop>=100000000) else "No" ,
                     "Yes" if (population_check[0]=="Yes" and total_tax_real_prop>=150000000) else "No" ,
                     "Yes" if (population_check[0] == "Yes" and total_tax_real_prop >= 250000000) else "No",
                     ]

        ## benefit for data center
        benefit_bol_array=[
            "Yes" if irs_sector=="Data processing, hosting, and related services" else "No",
            "Yes" if promised_jobs>=20 else "No",
            "Yes" if meets_capex.count("Yes")>0 else "No"
        ]
        benefit_bol="Yes" if benefit_bol_array.count("Yes")==3 else "No"

        ## minimum capex for distribution center
        minimum_capex_bol="Yes" if machinery>=5000000 else "No"


        ## benefit for manufacturing or distribution center
        benefit_for_manufacturing_bol_array=[
            "Yes" if high_level_category=="Manufacturing" else "No",
            "Yes" if high_level_category=="Information" else "No",
            "Yes" if (project_category=="Distribution center" and minimum_capex_bol=="Yes") else "No"
        ]

        ## main tab
        main_bol="Yes" if (benefit_for_manufacturing_bol_array[0]=="Yes" or benefit_for_manufacturing_bol_array[-1]=="Yes" or benefit_bol=="Yes") else "No"


        df_dict=defaultdict(list)
        for i in range(11):
            df_dict["Year"].append(i)
            if main_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(state_local_sales_tax_rate*machinery)
                else:
                    df_dict["value"].append(anual_expenditure[i]*state_local_sales_tax_rate)
        self.main_bol=main_bol
        path = georgia_config.__file__
        file = open(path, "w")

        file.write("sub_array={}".format(df_dict["value"]))
        file.close()


        return df_dict
