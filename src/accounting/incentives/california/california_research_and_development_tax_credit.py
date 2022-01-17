from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
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
        year = 10
        final_value = self.final_return_info
        npv_value = []
        string_name = []
        start_year = 1

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
        # this sheet is affected by round errors

        df_dict=defaultdict(list)
        base_rate=0.03
        year=10
        research_and_develop=self.npv_dicts["Research & development"]
        sales=self.npv_dicts["Sales"]
        #this look up is alittle bit in accurate
        # coperate_tax_rate=self.pnl_input['state_corporate_income_tax_apportionment']
        coperate_tax_rate=0.1213
        # some of them we can use fixed rate
        rate=["",0.03,0.03,0.03,0.03,0.03]



        array=[(research_and_develop[i]+research_and_develop[i+1]+research_and_develop[i+2])/((sales[i]+sales[i+1]+sales[i+2])*coperate_tax_rate) for i in range(3,9)]


        for i in range(len(array)-1):
            rate.append(array[i])
        base_amount_1=[]

        for i in range(1,7):
            if i<3:
                num_array=[sales[1]]

                base_amount_1.append(sales[1] * coperate_tax_rate)
            else:

                num_array.append(sales[i-1])

                base_amount_1.append(numpy.mean(num_array)*coperate_tax_rate)


        base_amount_2=[]
        num_array_2=[]
        for i in range(2,8):
            num_array_2=[sales[i],sales[i+1],sales[i+2],sales[i+3]]
            value=(numpy.mean(num_array_2)*coperate_tax_rate)

            base_amount_2.append(value)
        base_amount=[""]
        for i in range(len(base_amount_1)-1):
            base_amount.append(base_amount_1[i])
        for i in range(len(base_amount_2)-1):
            base_amount.append(base_amount_2[i])


        multiply_base=[""]

        for i in range(1,11):
            multiply_base.append(base_amount[i]*rate[i])
        excess=[""]
        for i in range(1,11):
            value=0 if ((research_and_develop[i]-multiply_base[i])<0) else research_and_develop[i]-multiply_base[i]
            excess.append(value)
        base_by_50=[""]
        for i in range(1,11):
            base_by_50.append(research_and_develop[i]*0.5)
        minimum_two_line=[0]
        for i in range(1,11):
            min_array=[base_by_50[i],excess[i]]
            minimum_two_line.append(min(min_array)*0.15)
        df_dict["year"]=[i for i in range(11)]
        df_dict["value"]=minimum_two_line
        self.main_bol="Yes"
        return df_dict






