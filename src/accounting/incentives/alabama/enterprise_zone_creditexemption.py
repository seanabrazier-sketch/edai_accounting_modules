from accounting.incentives import *
from util.capex import PersonalProperty,RealProperty, IndustryType
from collections import defaultdict
from util.npv import npv
from accounting.data_store import *
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self,**kwargs):
        self.capex = kwargs['capex']
        self.npv_dicts = kwargs['pnl'].npv_dicts
        self.all_input=kwargs
        self.pnl_input=kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.zone_type_1 = kwargs['zone_type_1']
        self.zone_type_2 = kwargs['zone_type_2']
        self.zone_type_3 = kwargs['zone_type_3']
        self.get_zone = self.get_zone()
        self.county = self.get_county_name()
        self.benefit_section_11_info=self.benefit_section_11()
        self.capex_tab_info=self.capex_tab()
        self.benefit_section_5_info=self.benefit_section_5()
        self.enterprise_zone_info=self.enterprise_zone()
        self.final_return_info=self.final_return()

    def estimated_eligibility(self) -> bool:
        if self.main_bol == "Yes":
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        from util.npv import excel_npv
        self.discount_rate = self.project_level_inputs["Discount rate"]
        year = 6
        final_value = self.final_return_info
        npv_value = []
        string_name = []
        start_year = 0

        for i in self.final_return_info:
            if i != "year" and i != "Year":
                array_value=[]

                string = "npv_{}".format(i)
                string_name.append(string)
                for k in range(11):
                    if k<start_year:
                        array_value.append("Base")
                        continue

                    if k>year:
                        array_value.append(0)
                    else:

                        array_value.append(final_value[i][k])

                value = excel_npv(self.discount_rate, final_value[i][start_year:year + start_year])
                final_value[i] = array_value
                npv_value.append(value)

        final_value["NPV_Name"] = string_name
        final_value["NPV_Value"] = npv_value

        return final_value

    def get_county_name(self):
        county = []
        county_list = self.all_input['county_drop_down_list']

        for i in county_list:
            try:
                index = i.index(", Alabama")
                value = i.replace("Alabama", "AL")
                county.append(value)
                break
            except:
                try:
                    index = i.index(", AL")
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

    def benefit_section_11(self):
        json_return = {
            "Sales and use tax on qualifying purchases during construction": "",
            "Income tax credit": "",
            "Business privilege tax": "* Lumped in with income tax"

        }
        return json_return

    def benefit_section_5(self):
        json_return={
            "At least 30% of new hires hard-to-employ OR":("No",2500),
            "Capital investment OR":("Yes" if self.project_level_inputs["Promised jobs"]>5 else "No",self.capex_tab_info['Total benefit']/self.project_level_inputs['Promised jobs']),
            "Requires at least FTEs hired":("",5),
            "Training, up to $1K OR":("Yes",1000)
        }
        #dum this into a array value
        array=[json_return[i][1] for i in json_return if json_return[i][0]=="Yes"]


        max_val=max(array)

        json_return["Benefit per employee"]=max_val

        count_yes=len(array)


        json_return["bol"]="Yes" if count_yes>0 else "No"
        return json_return
    def capex_tab(self):
        json_return={
            "Tranche":(10000,90000,"Remaining"),
            "Share":(0.1,0.05,0.02)
        }
        json_return["Benefit"]=(json_return["Tranche"][0]*json_return["Share"][0],json_return["Tranche"][1]*json_return["Share"][1],((self.project_level_inputs["Promised capital investment"]-(json_return["Tranche"][0]+json_return["Tranche"][1]))*json_return["Share"][2]))

        json_return['Total benefit']=sum(json_return["Benefit"])

        return json_return
    def enterprise_zone(self):
        array=[self.zone_type_1,self.zone_type_2,self.zone_type_3]
        count=array.count("*Enterprise*")
        return_val="Yes" if count>0 else "No"
        return return_val
    def final_return(self):

        year=5
        def_dict=defaultdict(list)

        for i in range(year+1):
            if i ==1:
                if self.benefit_section_5_info['bol']=="Yes":
                    def_dict['Benefits'].append(self.benefit_section_5_info['Benefit per employee']*self.project_level_inputs['Promised jobs'])

                else:
                    def_dict['Benefits'].append(0)
            else:
                def_dict['Benefits'].append(0)


        for i in range(year+1):
            def_dict["year"].append(i)
            if self.enterprise_zone_info=="No":
                def_dict["Sales and use tax on qualifying purchases during construction"].append(0)
                def_dict['Income tax credit'].append(0)
                def_dict['Business priviledge tax'].append(0)
                def_dict['In Enterprise Zone'].append(0)
            else:
                if i ==0:
                    Construction_material_value=self.capex.amount(property_type=RealProperty.CONSTRUCTION_MATERIAL,industry_type=IndustryType.INDUSTRIAL)
                    state_and_local_tax=self.pnl_input['state_local_sales_tax_rate']
                    def_dict['Sales and use tax on qualifying purchases during construction'].append(Construction_material_value*state_and_local_tax)
                    def_dict['Income tax credit'].append(0)
                    def_dict['Business priviledge tax'].append(0)
                    sum_val=def_dict['Sales and use tax on qualifying purchases during construction'][-1]+def_dict['Income tax credit'][-1]+def_dict['Business priviledge tax'][-1]+def_dict['Benefits'][i]
                    def_dict['In Enterprise Zone'].append(sum_val)
                else:
                    def_dict['Income tax credit'].append(self.npv_dicts['State corporate income tax'][i])
                    def_dict['Business priviledge tax'].append(0)
                    def_dict['Sales and use tax on qualifying purchases during construction'].append(0)
                    sum_val = def_dict['Sales and use tax on qualifying purchases during construction'][-1] + \
                              def_dict['Income tax credit'][-1] + def_dict['Business priviledge tax'][-1] + \
                              def_dict['Benefits'][i]
                    def_dict['In Enterprise Zone'].append(sum_val)
        self.main_bol=self.enterprise_zone_info

        return def_dict

