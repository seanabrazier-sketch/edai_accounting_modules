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
        ##necessary variables
        ## get sales aportionment
        sales_apportionment=sales_apportionment_df["Est. home state sales"]["Idaho"]
        sales=self.npv_dicts["Sales"]
        default_rate=[0.1667,0.3333,0.5,0.6667,0.8333]
        research_develope=self.npv_dicts["Research & development"]
        ## main tab
        main_bol="Yes"
        self.main_bol=main_bol
        main_array_1=[]
        for i in range(1,6):
            main_array_1.append(research_develope[i]*0.03)
        fixed_base_percentage=[]
        gross_receipt_aportionment=[]
        sales_slice=[]
        for i in range(6,11):
            sales_slice.append(sales[i])
            gross_receipt_aportionment.append(sales[i]*sales_apportionment)
            value1=sales[i]*sales_apportionment*default_rate[i-6]
            fixed_base_percentage.append(min([research_develope[i]/value1,0.16]))
        gross_receipt_array=[]
        for i in range(5,11):
            slice_value=sales[i-4:i]

            sum_product=[i*sales_apportionment for i in slice_value]
            sum_val=sum(sum_product)

            gross_receipt_array.append(sum_val/4)

        base_amount=[]

        for i in range(len(fixed_base_percentage)):
            base_amount.append(gross_receipt_array[i+1]*fixed_base_percentage[i])

        subtract_base_from=[i-j for i,j in zip(gross_receipt_aportionment,base_amount)]
        multiple_qre=[i*0.5 for i in sales_slice]
        smaller_of_line=[min([i,j]) for i,j in zip(multiple_qre,subtract_base_from)]
        final_val=[i*0.05 for i in smaller_of_line]

        for i in final_val:
            main_array_1.append(i)
        df_dict=defaultdict(list)
        main_array_1.insert(0,0)
        year=[i for i in range(11)]
        df_dict["year"]=year
        df_dict["value"]=main_array_1
        return df_dict