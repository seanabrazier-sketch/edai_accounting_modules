from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Utah')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.locating_EZ_zone = 'No'
        self.special_localities = special_localities_df['Zone Type 1']['Cache County, UT'] #fix later
        self.locating_ez = 'No'
        self.new_hire = 750
        self.bonus_wage_bump = 500
        self.bonus_agg_value = 750
        self.bonus_employer_health = 200
        self.max_fte_payout = 30
        self.annual_tax_credit = .05
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if self.locating_EZ_zone == 'Yes' and self.special_localities == 'Rural':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output_list = [(self.new_hire * max(self.project_level_inputs['Promised jobs'], self.max_fte_payout)),
                       (self.bonus_wage_bump * max(self.project_level_inputs['Promised jobs'], self.max_fte_payout)),
                       (self.bonus_agg_value * max(self.project_level_inputs['Promised jobs'], self.max_fte_payout)),
                       (self.bonus_employer_health * max(self.project_level_inputs['Promised jobs'], self.max_fte_payout)),
                       self.annual_tax_credit * min(750000,
                                                    (self.capex.amount(
                                                        industry_type=self.pnl_inputs['industry_type'],
                                                        property_type=RealProperty.CONSTRUCTION_MATERIAL)
                                                     + self.capex.amount(
                                                                industry_type=self.pnl_inputs['industry_type'],
                                                                property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                                                     ))
                       ]
        nums1 = [0.0, output_list[0]]
        nums2 = [0.0, output_list[1]]
        nums3 = [0.0, output_list[2]]
        nums4 = [0.0, output_list[3]]
        nums5 = [output_list[4]]

        for j in range(1, 10):
            if len(nums1[2:]) + 1 >= 1 and len(nums2[2:]) + 1 >= 1 and len(nums3[2:]) + 1 >= 1 \
                    and len(nums4[2:]) + 1 >= 1:
                nums1.append(0)
                nums2.append(0)
                nums3.append(0)
                nums4.append(0)
            else:
                nums1.append(output_list[0])
                nums2.append(output_list[1])
                nums3.append(output_list[2])
                nums4.append(output_list[3])
        for j in range(1, 11):
            if len(nums5[1:]) + 1 >= 10:
                nums5.append(0.0)
            else:
                nums5.append(output_list[4])

        incentives = []
        for i, j, k, l, m in zip(nums1, nums2, nums3, nums4, nums5):
            if self.locating_ez == 'Yes' and self.special_localities == 'Rural':
                incentives.append(i + j + k + l + m)
            else:
                incentives = [0.0] * 11

        return incentives
