from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
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
        #RD Tax Credit
        rd_tax_credit_array=[]
        research_and_development=self.npv_dicts['Research & development']
        research_and_development=research_and_development[1:]
        for i in range(len(research_and_development)-2):
            array1=research_and_development[i:i+3]
            array=research_and_development[i:i+2]
            rd_tax_credit_array.append(array1[2]-numpy.mean(array))

        rd_tax_credit_excess=[0,0,0]
        for i in rd_tax_credit_array:
            rd_tax_credit_excess.append(i*0.03)




        ## take npv of this rd_tax_credit acess then we are done for rd_tax_credit
        promised_jobs=self.project_level_inputs["Promised jobs"]
        promised_wage=self.project_level_inputs["Promised wages"]
        #employer sponsor health_insurance
        year=2
        employer_sponsor_array =[0]

        employer_sponsor_array.append(promised_jobs*1000)
        employer_sponsor_array.append(promised_jobs*1000)
        for i in range(8):
            employer_sponsor_array.append(0)



        #Project meets
        per_capital_income=self.all_input["state_to_per_capita_income"]["Colorado"]
        county_capital_income=self.all_input["county_to_per_capita_income"][self.county] if len(self.county)>0 else per_capital_income
        per_capital_less75="Yes" if county_capital_income<0.75*per_capital_income else "No"

        county_unemployment=self.all_input["county_to_unemployment_rate"][self.county] if len(self.county)>0 else 0
        state_unempoyment=self.all_input["state_to_unemployment_rate"]["Colorado"]
        ## this is an error and we need to raise this to Sean
        ## in the excel sheet this should return no instead of Yes

        unem_greater25="Yes" if county_unemployment>state_unempoyment*1.25 else "No"
        population_growth="Not model"

        projects_meets_main_bol="Yes" if (unem_greater25=="Yes" or population_growth=="Yes" or per_capital_less75=="Yes") else "No"

        #Job Training Tax Credit
        cost_to_train=self.all_input["workforce_programs_ipj_map"]["Costs to train employee"]

        jobs_traning_tax_credit_value=cost_to_train*promised_jobs*0.12
        jobs_training_tax_credit_array=[0]
        jobs_training_tax_credit_array.append(jobs_traning_tax_credit_value)
        for i in range(9):
            jobs_training_tax_credit_array.append(0)



        #Investment tax credit
        total_personal_property=self.capex.amount(property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT,industry_type=self.pnl_input["industry_type"])+self.capex.amount(property_type=PersonalProperty.FIXTURES,industry_type=self.pnl_input["industry_type"])
        ## this missing else condition value for else
        # need to bring this to Sean

        investment_tax_credit_value=0.03*total_personal_property


        investment_tax_credit_array=[0]
        investment_tax_credit_array.append(investment_tax_credit_value)
        for i in range(9):
            investment_tax_credit_array.append(0)




        #new employee credit

        bol_array=[("Yes",1100),("No",500),("Yes" if self.zone_type_1=="Enhanced Rural Enterprise Zone" else "No",2000),("No",500)]
        value_array=[i[1] for i in bol_array if i[0]=="Yes"]

        sum_val=sum(value_array)


        new_employee_credit_per_job_final_val=promised_jobs*sum_val if projects_meets_main_bol=="Yes" else 0
        new_employee_credit_array=[0]
        new_employee_credit_array.append(new_employee_credit_per_job_final_val)
        for i in range(9):
            new_employee_credit_array.append(0)

        self.main_bol=projects_meets_main_bol

        df_dict=defaultdict(list)
        year=10
        for i in range(year+1):
            df_dict["year"].append(i)
            if self.main_bol=="Yes":
                if i==0:
                    df_dict["value"].append(0)
                else:
                    df_dict["value"].append(investment_tax_credit_array[i]+jobs_training_tax_credit_array[i]+new_employee_credit_array[i]+employer_sponsor_array[i]+rd_tax_credit_excess[i])
            else:
                df_dict["value"].append(0)
        return df_dict

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Colorado")
                value = i.replace("Colorado", "CO")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", CO")
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

## this module is done only need to confirm with sean about the above.




