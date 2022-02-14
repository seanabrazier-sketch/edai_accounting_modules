from accounting.incentives import *
import pandas
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from util.npv import npv
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self,**kwargs):
        self.capex = kwargs['capex']
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.all_input=kwargs
        self.pnl_input=kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.urban_rural_df_info=self.urban_rural_df()
        self.meets_capex_df_info=self.meets_capex_df()
        self.county=self.get_county_name()
        self.final_return_info=self.final_return()

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year = 3

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
    def urban_rural_df(self):
        minimum_capex=[5000000,2500000,1000000,500000,1000000,500000,100000]
        minimum_new_jobs=[25,25,25,25,5,5,5]
        minimum_wages=[1,1.25,1.5,2,1,1.25,1.5]
        name=["Urban","Urban","Urban","Urban","Rural","Rural","Rural"]
        data={"Urban":name,"Minimum capex":minimum_capex,"Minimum new jobs":minimum_new_jobs,"Minimum wages":minimum_wages}
        df=pandas.DataFrame(data=data)
        return df
    def meets_capex_df(self):
        promised_capital_investment=self.project_level_inputs["Promised capital investment"]
        urban=self.urban_rural_df_info["Urban"].tolist()
        minimum_capex=self.urban_rural_df_info["Minimum capex"].tolist()
        meet_capex=["Yes" if (str(i)=="Urban" and promised_capital_investment>=float(k)) else "No" for i,k in zip(urban,minimum_capex)]
        promised_job=self.project_level_inputs["Promised jobs"]
        minimum_new_jobs=self.urban_rural_df_info["Minimum new jobs"].tolist()
        meet_job=["Yes" if (str(i)=="Urban" and promised_job>=float(k)) else "No" for i,k in zip(urban,minimum_new_jobs)]
        promised_wages=self.project_level_inputs['Promised wages']
        prevailing_wages_county=None
        try:
            prevailing_wages_county=self.project_level_inputs['Prevailing wages county'][self.county]
        except:
            prevailing_wages_county = self.project_level_inputs['Prevailing wages']["Arizona"]
        minimum_wage=self.urban_rural_df_info['Minimum wages'].tolist()
        meet_wage=["Yes" if (i =="Urban" and promised_wages>=k*prevailing_wages_county) else "No" for i,k in zip(urban,minimum_wage)]
        meet_3=["Yes" if (i=="Yes" and k=="Yes" and l=="Yes") else "No" for i,k,l in zip(meet_capex,meet_job,meet_wage)]
        data={"Meets capex":meet_capex,"Meets jobs":meet_job,"Meets wages":meet_wage,"Meets all three":meet_3}
        df=pandas.DataFrame(data=data)

        return df
    def final_return(self):
        count_yes=self.meets_capex_df_info["Meets all three"].tolist()
        count_val=count_yes.count("Yes")
        bol="Yes" if count_val >0 else "No"
        year=3
        promised_jobs=self.project_level_inputs["Promised jobs"]
        #name default is not used yet in this
        name_default="Urban" if len(self.county)>0 else self.county
        value=3000
        df_dict=defaultdict(list)
        for i in range(year+1):
            df_dict["year"].append(i)
            if bol=="No":
                df_dict["value"].append(0)
            else:
                if i==0:
                    df_dict["value"].append(0)
                else:

                    df_dict["value"].append(promised_jobs*value)


        ## NPV formula in excel sheet returns the NPV of an array but the others are blank cells so this will get discounted wrong
        self.main_bol=bol


        return df_dict



    def get_county_name(self):
        county=[]
        county_list=self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index=i.index(", AZ")
                county.append(i)
                break
            except:
                pass

        if len(county)>0:
            county=county[0]
        else:
            county

        return county
