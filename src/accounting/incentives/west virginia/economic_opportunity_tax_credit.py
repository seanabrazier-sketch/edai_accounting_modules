import numpy as np
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType

from accounting.incentives import *
from accounting.data_store import *
from itertools import repeat


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.thirteen_year_benefit = 13
        self.twenty_year_benefit = 20
        self.project_level_inputs = kwargs['project_level_inputs']
        self.max_gross_receipts = 9953650
        self.capex = kwargs['capex']
        self.high_level_list = ["Manufacturing", "Information"]
        self.project_cat_list = ["R&D Center", "Corporate Headquarters", "Distribution Center",
                                 "Capital-intensive manufacturer", "Labor-intensive manufacturer"]
        self.lst = pd.DataFrame([[10, 'Small business only', .10],
                                 [15, 'Corporate HQs only', .10],
                                 [20, "", .20],
                                 [280, "", .25],
                                 [520, "", .30]])
        self.lst.columns = ['Min jobs', 'Nuance', 'Benefit share of capex']

        self.lst2 = pd.DataFrame([['Less than 4 years', 0.0],
                                  ['4 years or less than 6', .3333],
                                  ["6 years or less than 8", .6666],
                                  ["8 years or more", 1.0]])
        self.lst2.columns = ['Useful life in WV', 'Useful life %']

        self.ME_four_to_six_years = self.lst2['Useful life %'].values[1]
        self.Fixtures_less_than_four = self.lst2['Useful life %'].values[0]
        self.Structure_eight_years = self.lst2['Useful life %'].values[3]

        self.qualified_capex_amount = ((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                          property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) \
                                        * self.ME_four_to_six_years) +
                                       (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                          property_type=PersonalProperty.FIXTURES) \
                                        * self.Fixtures_less_than_four) +
                                       (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                          property_type=RealProperty.CONSTRUCTION_MATERIAL) \
                                        * self.Structure_eight_years))

    def estimated_eligibility(self) -> bool:
        # maybe check with sean about this one, checking what are requirements and what are benefits
        # ask evan if this code is correct

        if self.project_level_inputs['Promised jobs'] >= 20 \
                and any(s in self.project_level_inputs['High-level category'] for s in self.high_level_list) \
                or any(s in self.project_level_inputs['Project category'] for s in self.project_cat_list):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        if self.project_level_inputs['High-level category'] == "Information":
            num = 20
        elif self.project_level_inputs['Project category'] == "Corporate Headquarters":
            num = 13
        else:
            num = 10

        idx = self.lst['Min jobs'].sub(self.project_level_inputs['Promised jobs']).abs().idxmin()
        df1 = self.lst.loc[[idx]]
        num1 = df1['Benefit share of capex'].values[0]

        if self.project_level_inputs['Project category'] == "Corporate Headquarters" and \
                self.project_level_inputs['Promised jobs'] > self.lst['Min jobs'].values[1]:
            num2 = self.lst['Benefit share of capax'].values[1]
        else:
            num2 = 0

        if self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)'] \
                < self.max_gross_receipts and self.project_level_inputs['Promised jobs'] >= self.lst['Min jobs'].values[
            0]:
            num3 = self.lst['Benefit share of capex'].values[0]
        else:
            num3 = 0

        max_value = max(num1, num2, num3)
        benefit_prorate_ten_years = self.qualified_capex_amount * max_value
        output = benefit_prorate_ten_years / num

        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:2]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
