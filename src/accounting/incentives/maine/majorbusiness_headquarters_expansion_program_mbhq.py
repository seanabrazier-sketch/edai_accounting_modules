from accounting.incentives import *
import numpy
from accounting.incentives.alabama.jobs_act_incentives_jobs import IncentiveProgram as jobs
from collections import defaultdict
from util.npv import npv
from util.necessary import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from accounting.data_store import *

from accounting.incentives.maine.employment_tax_increment_financing_program_etif import IncentiveProgram as subclass

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        # self.sub_class=subclass(**kwargs)
        self.capex = kwargs['capex']
        self.all_input=kwargs

        self.pnl_input=kwargs["pnl_inputs"]
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.default_year=[i for i in range(11)]
        self.final_return_info=self.final_return()
    def estimated_eligibility(self)->bool:
        if self.main_bol=="Yes":
            return True
        else:
            return False

    def estimated_incentives(self)->List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year = 10
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
        ##requirement
        promised_capital=self.project_level_inputs["Promised capital investment"]
        promised_job=self.project_level_inputs["Promised jobs"]

        requirement_array_bol=[
            "Yes" if promised_capital>=35000000 else "No",
            "Yes" if promised_job>=800 else "No"
            "No",
            "No",

        ]
        self.main_bol="Yes" if requirement_array_bol.count("Yes")==4 else "No"

        array1=[]
        array2=[]
        array3=[]
        main_array=[]
        for i in range(11):
            if self.main_bol=="Yes":
                    if i ==0 :
                        array1.append(0)
                        array2.append(0)
                        array3.append(0)
                        main_array.append(0)
                    else:
                        array1.append(promised_capital*0.02)

                        if i<2:
                            array2.append(0)
                            array3.append(0)
                        else:
                            array2.append(sum(array1[0:-1]))
                            array3.append(16000000-array2[-2] if array2[-1]>16000000 else array2[-1]-array1[-2])
                        if array2[-1]>16000000:
                            main_array.append(max([array3[-1],0]))
                        else:
                            main_array.append(array1[-1])

            else:
                    main_array.append(0)
        df_dict=defaultdict(list)
        df_dict["year"]=self.default_year
        df_dict["value"]=main_array
        return  df_dict
