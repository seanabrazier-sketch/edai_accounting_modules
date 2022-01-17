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
        self.county=self.get_county_name()

        self.get_zone = self.get_zone()
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
        #necessary variables
        prevailing_wages=None
        if isinstance(self.county,str):

            prevailing_wages=self.project_level_inputs["Prevailing wages county"][self.county]
        else:
            prevailing_wages=self.project_level_inputs["Prevailing wages"]["Florida"]
        #inheritance
        self.prevailing_wages=prevailing_wages
        zone_1=self.zone_type_1
        promised_wage=self.project_level_inputs["Promised wages"]
        promised_jobs=self.project_level_inputs["Promised jobs"]
        high_level_category=self.project_level_inputs["High-level category"]
        irs_sector=self.project_level_inputs["IRS Sector"]
        project_category=self.project_level_inputs["Project category"]
        irs_sector_name=irs_sector_shares_df.index.tolist()
        ## High impact "portions" of the following sectors
        irs_sector_lookup=None
        try:
            irs_sector_lookup=irs_sector_name[irs_sector]
        except:
            irs_sector_lookup=False
        high_impact_array=[
            "Yes" if high_level_category=="Manufacturing" else "No",
            "Manual",
            "Manual",
            ## need to get IRS sector Tab
            "Yes" if irs_sector_lookup!=False else "No",
            "Yes" if high_level_category=="Information" else "No",
            "Yes" if irs_sector=="Computer and electronic product manufacturing" else "No",
            "Yes" if irs_sector=="Transportation equipment manufacturing"   else "No",
            "Yes" if project_category=="Corporate headquarters" else "No"
        ]
        ## for inheritance

        self.high_impact_array=high_impact_array

        ## Sectors
        high_impact_sector_bol=("Yes" if high_impact_array.count("Yes")>0 else "No",2000)
        export_bonus_default_bol=("-",2000)
        sector_val=high_impact_sector_bol[1] if (high_impact_sector_bol[0]=="Yes" or export_bonus_default_bol[0]=="Yes") else 0


        ## miscellaneous
        brownfield_bonus_default_bol="No"
        local_math_default_bol="No"
        miscellaneous_val=high_impact_sector_bol[1] if (brownfield_bonus_default_bol=="Yes" or export_bonus_default_bol[0]=="Yes") else 0

        ## starting math
        starting_benefit_per_job_bol=("-",3000)
        starting_benefit_if_rural=("Yes" if zone_1=="Rural" else "No",6000)

        starting_math_value=starting_benefit_if_rural[1] if starting_benefit_if_rural[0]=="Yes" else starting_benefit_per_job_bol[1]
        # Minimum county wages
        minimum_county_wages_bol1=("Yes" if (promised_wage>= prevailing_wages*1.5) else "No")
        minimum_county_wages_bol2 = ("Yes" if (promised_wage >= prevailing_wages * 2) else "No")
        minimum_val_yes=[1000 if minimum_county_wages_bol1=="Yes" else 0,2000 if minimum_county_wages_bol2=="Yes" else 0]
        minimum_county_val=max(minimum_val_yes)

        ## total benefits per job calculation
        total_benefits_val=starting_math_value+sector_val+miscellaneous_val+minimum_county_val

        ## Requirement
        bottom_requirement=["Yes" if promised_wage>=prevailing_wages*1.15 else "No",
                            "Not Included",
                            "Yes" if promised_wage>=prevailing_wages*1.15 else "No"

                            ]


        requirement_bol_array=["Yes" if promised_jobs>=10 else "No",
                               "Yes" if high_impact_array.count("Yes") >0 else "No",
                                "Yes" if bottom_requirement.count("Yes") >0 else "No"

                               ]

        ## main tab
        main_bol="Yes" if requirement_bol_array.count("Yes")==3 else "No"
        default_val=1500000
        df_dict=defaultdict(list)
        year=4
        for i in range(11):
            df_dict["year"].append(i)
            if main_bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:
                    ## there is a potential missunderstanding in this formula
                    df_dict["value"].append(min([default_val,(total_benefits_val/year)*promised_jobs]))
        self.main_bol=main_bol

        return df_dict

    def get_zone(self):

        try:
            zone_type_1 = list_of_special_localities["Zone Type 1"]
            self.zone_type_1 = zone_type_1[self.county]
            if len(self.zone_type_1) == 0:
                self.zone_type_1 = "-"
        except:
            self.zone_type_1 = "-"
        try:
            zone_type_2 = list_of_special_localities["Zone Type 2"]
            self.zone_type_2 = zone_type_2[self.county]
            if len(self.zone_type_2) == 0:
                self.zone_type_2 = "-"
        except:
            self.zone_type_2 = "-"
        try:
            zone_type_3 = list_of_special_localities["Zone Type 3"]
            self.zone_type_3 = zone_type_3[self.county]
            if len(self.zone_type_3) == 0:
                self.zone_type_3 = "-"

        except:
            self.zone_type_3 = "-"

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Florida")
                value = i.replace("Florida", "FL")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", FL")
                    county.append(i)
                except:
                    pass

        if len(county) > 0:
            county = county[0]
        else:
            county

        return county

