from accounting.incentives import *
from accounting.data_store import *
from util.capex import SHARES_INDUSTRIAL, RealProperty, IndustryType, PersonalProperty
from itertools import repeat


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Wisconsin')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = special_localities_df['Zone Type 1']['Adams County, WI']
        self.share_wages = .10
        self.add_bonus = .05
        #self.user_input = grant_estimates_misc_df['Amount']['Costs to train employee']
        self.cost_to_train_employee = kwargs['workforce_programs_ipj_map']['Costs to train employee']
        self.job_training_credit = .50
        self.personal_property_investment = .03
        self.real_property_investment = .05
        self.capex = kwargs['capex']
        self.total_capital_investment = 1000000
        self.capex_per_FTE = self.project_level_inputs['Promised capital investment'] \
                             / self.project_level_inputs['Promised jobs']

    def estimated_eligibility(self) -> bool:
        # if self.special_localities == 'Distressed/Tier I':
        return True

    def estimated_incentives(self) -> List[float]:
        output = self.share_wages * self.project_level_inputs['Promised jobs'] * self.project_level_inputs[
            'Promised wages']

        nums1 = [output]
        for j in range(0, 9):
            if len(nums1[0:]) + 1 <= 3:
                nums1.append(output)
            else:
                nums1.append(0.0)

        if self.special_localities == 'Distressed/Tier I':
            nums2 = [True]
        else:
            nums2 = [False]

        output2 = self.add_bonus * self.project_level_inputs['Promised jobs'] * self.project_level_inputs[
            'Promised wages']
        for j in range(0, 9):
            if len(nums2[0:]) + 1 <= 3 and self.special_localities != 'Distressed/Tier I':
                nums2.append(output2)
            else:
                nums2.append(0.0)

        nums3 = [self.cost_to_train_employee * self.job_training_credit * self.project_level_inputs['Promised jobs']]
        nums3.extend(repeat(0.0, 10))

        output3 = (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                     property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                   self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                     property_type=PersonalProperty.FIXTURES)) * self.personal_property_investment
        nums4 = [output3]
        for j in range(0, 9):
            if len(nums4[0:]) + 1 <= 3:
                nums4.append(output3)
            else:
                nums4.append(0.0)
        if (self.project_level_inputs['Promised capital investment'] < self.personal_property_investment) and \
                (self.capex_per_FTE >= 10000) or self.project_level_inputs['Promised capital investment'] \
                >= self.personal_property_investment:
            output4 = (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                         property_type=RealProperty.LAND) +
                       self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                         property_type=RealProperty.CONSTRUCTION_MATERIAL)) \
                      * self.real_property_investment
        nums5 = [output4]
        for j in range(0, 9):
            if len(nums5[0:]) + 1 <= 3:
                nums5.append(output4)
            else:
                nums5.append(0.0)

        start = [0.0]

        for x in zip(nums1, nums2, nums3, nums4, nums5):
            start.append(sum(x))

        incentives = []
        for j in start:
            if len(incentives[1:]) + 1 <= 3:
                incentives.append(j)
            else:
                incentives.append(0.0)

        return incentives
