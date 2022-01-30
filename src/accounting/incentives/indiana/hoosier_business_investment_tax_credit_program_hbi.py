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
        # self.sub_class=subclass(**kwargs)
        self.capex = kwargs['capex']
        self.all_input = kwargs

        self.pnl_input = kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.default_year = [i for i in range(11)]
        self.construction = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                              property_type=RealProperty.CONSTRUCTION_MATERIAL)
        self.land = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                              property_type=RealProperty.LAND)
        self.machine = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        self.fix = self.capex.amount(industry_type=self.pnl_input["industry_type"],
                                     property_type=PersonalProperty.FIXTURES)
        self.high_level = self.project_level_inputs["High-level category"]
        self.irs = self.project_level_inputs["IRS Sector"]
        self.project_category = self.project_level_inputs["Project category"]
        self.promised_jobs = self.project_level_inputs["Promised jobs"]
        self.promised_wage = self.project_level_inputs["Promised wages"]
        self.promised_cap = self.project_level_inputs["Promised capital investment"]
        self.federal_minimum_wage = self.project_level_inputs["Federal minimum wage"]
        self.equipvalent_payroll_base = self.project_level_inputs["Equivalent payroll (BASE)"]
        self.discount_rate = self.project_level_inputs["Discount rate"]

        self.state_local_sale_tax_rate = self.pnl_input["state_local_sales_tax_rate"]
        self.rd = self.npv_dicts["Research & development"]
        self.total_real_and_personal_prop = self.construction + self.machine + self.fix
        self.state_corporate_income_tax=self.npv_dicts["State corporate income tax"]
        self.state_corporate_income_tax[0]=0
        self.state_ui_tax=self.npv_dicts["State UI tax"]
        self.total_personal_prop = self.fix + self.machine
        self.property_tax_rate = self.pnl_input["property_tax_rate"]
        self.state_local_sale_tax=self.npv_dicts["State/local sales tax"]
        self.property_tax = self.npv_dicts["Property tax"]
        self.annual_exp = self.npv_dicts["Annual capital expenditures option 2"]
        self.attraction = self.project_level_inputs["Attraction or Expansion?"]
        self.final_return_info = self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year = 1
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
        ## logistics
        logistic_bol="Yes" if self.project_category=="Distribution center" else "No"
        ## user input
        df=discretionary_incentives_df
        self.main_bol="Yes"
        df.index=discretionary_incentives_df["Region/state"].tolist()

        wd_sector=df["W&D sector?"]["Indiana"].tolist()
        inc=df["Inc/capex"]["Indiana"].tolist()
        industry_activities=df["Industry activities"]["Indiana"]
        average_arr=[]

        for i in range(len(wd_sector)-1):
            try:
                value=float(wd_sector[i])
                if value==0:
                    average_arr.append(float(inc[i]))
            except:
                pass


        average_val=sum(average_arr)/len(average_arr)
        # not yet embed
        #default now
        default_val=average_val
        eligible_capex=self.machine*default_val if self.main_bol=="Yes" else 0
        # eligible_capex=self.machine*average_val if self.main_bol=="Yes" else 0
        array1=[]
        sum_val=self.construction+self.machine
        eligible_capex2=sum_val*default_val if self.main_bol=="Yes" else 0

        average_arr2=[]
        for i in range(len(industry_activities) - 1):
            try:

                if industry_activities[i] == "Warehousing and Distribution":
                    average_arr2.append(float(inc[i]))
            except:
                pass

        average_val2=sum(average_arr2)/len(average_arr2)
        default_val2=average_val2

        logistic_array=[]
        for i in range(11):
            if self.main_bol=="Yes":
                if i==0:
                    array1.append(0)
                    logistic_array.append(0)
                    continue
                if i==1:
                    logistic_array.append(eligible_capex2*default_val2)
                    array1.append(eligible_capex*default_val)
                    continue
                else:
                    array1.append(0)
                    logistic_array.append(0)
            else:
                logistic_array.append(0)
                array1.append(0)

        choose_val=logistic_array[1] if logistic_bol=="Yes" else array1[1]
        main_array=[]
        for i in range(11):
            if self.main_bol=="Yes":
                if i==0:
                    main_array.append(0)
                    continue
                if i==1:
                    main_array.append(min([choose_val,self.state_corporate_income_tax[1]]))
                    continue
                else:
                    main_array.append(0)
            else:
                main_array.append(0)
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return df_dict



