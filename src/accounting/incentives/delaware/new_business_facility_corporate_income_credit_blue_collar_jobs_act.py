from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
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
    def final_return(self):
        ## needed variable
        #g11
        prommised_jobs=self.project_level_inputs["Promised jobs"]
        #G13
        promised_capital_investment=self.project_level_inputs["Promised capital investment"]
        #g8
        high_level_category=self.project_level_inputs["High-level category"]
        #g9
        project_category=self.project_level_inputs["Project category"]
        #g7
        irs_sector=self.project_level_inputs["IRS Sector"]

        df_dict=defaultdict(list)

        ## Eligibility section
        ## sector tab

        eligibility_sector_bol = ["Yes" if high_level_category == "Manufacturing" else "No",
                                  "Yes" if high_level_category == "Wholesale trade" else "No",
                                  "Yes" if project_category == "Scientific, agricultural or industrial research, development or testing" else "No",
                                  "Yes" if irs_sector == "Data processing, hosting, and related services" else "No",
                                  "Yes" if irs_sector == "Professional, scientific, and technical services" else "No",
                                  "n/a",
                                  "n/a",
                                  "Yes" if high_level_category=="Information" else "No",
                                  "Yes" if high_level_category =="Information" else "No",
                                  "n/a",
                                  "n/a"]

        minimum_jobs="Yes" if prommised_jobs>=5 else "No"

        sector_requirement="Yes" if eligibility_sector_bol.count("Yes")>0 else "No"

        #eligibility min capex
        total_amount="Yes" if promised_capital_investment>=200000 else "No"
        per_employee_amount="Yes" if (promised_capital_investment/prommised_jobs)>=40000 else "No"
        min_capex="Yes" if (total_amount=="Yes" or per_employee_amount=="Yes") else "No"


        ## benefit additional bonus
        in_targeted_growth_area="No"
        benefit_additional_bonus_bol="Yes" if (minimum_jobs=="Yes" and min_capex=="Yes" and in_targeted_growth_area=="Yes") else "No"

        ## benefit standard
        benefit_standard_bol="Yes" if (minimum_jobs=="Yes" and min_capex=="Yes") else "No"


        #main_tab
        main_bol="Yes" if (minimum_jobs=="Yes" and min_capex=="Yes") else "No"


        ##generate array:
        benefit_additional_credit_per_job_array=[]

        benefit_additional_credit_per_100k_array=[]

        benefit_standard_credit_per_job_array=[]

        benefit_standard_credit_per_100k_array=[]



        for i in range(11):
            if main_bol=="No":

                benefit_additional_credit_per_job_array.append(0)
                benefit_additional_credit_per_100k_array.append(0)
                benefit_standard_credit_per_job_array.append(0)
                benefit_standard_credit_per_100k_array.append(0)
            else:
                if i ==0:
                    benefit_additional_credit_per_job_array.append(0)
                    benefit_additional_credit_per_100k_array.append(0)
                    benefit_standard_credit_per_job_array.append(0)
                    benefit_standard_credit_per_100k_array.append(0)
                else:
                    benefit_additional_credit_per_job_array.append(prommised_jobs*500)
                    benefit_additional_credit_per_100k_array.append((promised_capital_investment/100000)*500)
                    benefit_standard_credit_per_job_array.append(prommised_jobs*500)
                    benefit_standard_credit_per_100k_array.append((promised_capital_investment/100000)*500)


        ## benefit to use array
        ## this also missing else argument need to raise this up with Sean
        benefit_to_use_array=[]
        for i in range(11):
            if benefit_additional_bonus_bol=="No":
                if i==0:
                    benefit_to_use_array.append(0)
                else:
                    benefit_to_use_array.append(benefit_standard_credit_per_100k_array[i]+benefit_standard_credit_per_job_array[i])

            else:
                if i==0:
                    benefit_to_use_array.append(0)
                else:
                    benefit_to_use_array.append(benefit_standard_credit_per_100k_array[i]+benefit_standard_credit_per_job_array[i]+benefit_additional_credit_per_job_array[i]+benefit_additional_credit_per_100k_array[i])


        ## final_array
        empty_array=[i*0 for i in range(11)]
        final_array=benefit_to_use_array if main_bol=="Yes" else empty_array
        df_dict["final_value"]=final_array
        df_dict["Benefit to use"]=benefit_to_use_array
        df_dict["Benefit additional bonus -- Credit Per Job"]=benefit_additional_credit_per_job_array
        df_dict["Benefit additional bonus -- Credit Per $100K of capex"]=benefit_additional_credit_per_100k_array
        df_dict["Benefit Standard -- Credit Per Job"]=benefit_standard_credit_per_job_array
        df_dict["Benefit Standard -- Credit Per $100k of capex"]=benefit_standard_credit_per_100k_array

        ## for inheritance
        self.main_bol=main_bol

        return df_dict


