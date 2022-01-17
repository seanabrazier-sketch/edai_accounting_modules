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
        ##needed variable
        promised_jobs=self.project_level_inputs["Promised jobs"]
        promised_wage=self.project_level_inputs["Promised wages"]
        df_dict=defaultdict(list)


        ##Eligibility Option 2
        eligibility_op2_minimum_jobs="Yes" if promised_jobs>=50 else "No"
        eligibility_op2_minimum_salaray="Yes" if promised_wage>= 118200 else "No"
        eligibility_op2_bol="Yes" if (eligibility_op2_minimum_salaray=="Yes" and eligibility_op2_minimum_jobs=="Yes") else "No"

        ## Eligibility Option 1
        eligibility_op1_minimum_jobs="Yes" if promised_jobs>= 200 else "No"
        eligibility_op1_minnimum_salary="Yes" if promised_wage>=70000 else "No"
        eligibility_op1_bol="Yes" if (eligibility_op1_minnimum_salary=="Yes" and eligibility_op1_minimum_jobs=="Yes") else "No"

        ## Eligibility
        eligibility_main_bol="Yes" if (eligibility_op1_bol=="Yes" or eligibility_op2_bol=="Yes") else "No"

        ## Benefit, option 2
        benefit_option_2_array_1=[]
        for i in range(11):
            if i==0:
                benefit_option_2_array_1.append(0)
            else:
                benefit_option_2_array_1.append(promised_wage*promised_jobs*0.05*0.4)


        benefit_option_2_main_bol="Yes"
        benefit_option_2_array_2=[]

        for i in range(11):
           if i==0:
               benefit_option_2_array_2.append(0)

           else:
               if benefit_option_2_main_bol=="Yes":
                  if promised_jobs<=200:
                      benefit_option_2_array_2.append(promised_jobs*promised_wage*0.25*0.05)

                  else:
                       if promised_jobs>200:
                           # this is where it gets the error
                            x=200*0.25*0.05*promised_wage

                            y=(promised_jobs-200)*(0.075/100)*0.05*promised_wage


                            benefit_option_2_array_2.append(x+y)

                       else:
                            benefit_option_2_array_2.append(0)

               else:
                   benefit_option_2_array_2.append(0)
        df_dict["Benefit, option 2 -- main"]=benefit_option_2_array_2

        ## Benefit option 1


        benefit_option1_main_bol=eligibility_main_bol
        benefit_option_1_array_2 = []
        for i in range(11):
           if i==0:
               benefit_option_1_array_2.append(0)
           else:
               if benefit_option1_main_bol=="No":
                   benefit_option_1_array_2.append(0)
               else:
                  if promised_jobs<=50:
                      benefit_option_1_array_2.append(promised_jobs*promised_wage*0.25*0.05)
                  else:
                       if promised_jobs>50:
                           x = 50 * 0.25 * 0.05 * promised_wage

                           y = (promised_jobs - 50) * (0.075 / 100) * 0.05 * promised_wage
                           benefit_option_1_array_2.append(x+y)
                       else:
                           benefit_option_1_array_2.append(0)
        df_dict["Benefit, option 1 -- main"]=benefit_option_1_array_2


        ## Main Tab
        main_bol="Yes" if (benefit_option_2_main_bol=="Yes" or benefit_option1_main_bol=="Yes") else "No"
        max_holding_credit_with_bonus=0.65
        max_holding_credit_with_bonus_array=[]
        main_array=[]
        for i in range(11):

            if main_bol=="No":
                main_array.append(0)
            else:
                if i == 0:
                    max_holding_credit_with_bonus_array.append(0)
                    main_array.append(0)
                else:

                    if benefit_option_2_main_bol=="Yes":
                        main_array.append(min([benefit_option_2_array_2[i],benefit_option_2_array_1[i]]))
                    else:
                        if benefit_option1_main_bol=="Yes":
                            main_array.append(min(df_dict["Benefit, option 1 -- Max withholding rate benefit"][i],benefit_option_1_array_2[i]))
                        else:
                            main_array.append(0)
        df_dict["value"]=main_array
        self.main_bol=main_bol

        return df_dict





