from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Vermont')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.first_three_years_benefit = .06
        self.after_three_year_benefit = .14
        self.sales = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.inflation = self.project_level_inputs['Inflation (employment cost index)']
        self.percent_base = .50
        self.credit_share_federal = .27

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        nums1 = [0.0, self.sales]
        for i in range(1, 10):
            nums1.append(nums1[-1] * (1 + self.inflation))

        nums2 = [0.0]

        for i in nums1[1:4]:
            nums2.append(i * self.first_three_years_benefit)

        calculations1 = pd.Series(nums1[1:])
        calculations1 = list(calculations1.rolling(3).mean())
        calculations1 = calculations1[3 - 1:]
        del calculations1[-1]

        nums3 = []
        for i in calculations1:
            nums3.append(i * self.percent_base)

        nums4 = []
        for i, j  in zip(nums1[4:], nums3):
            nums4.append(i - j)

        for i in nums4:
            nums2.append(i * self.after_three_year_benefit)

        incentives = []
        for i in nums2:
            incentives.append(i * self.credit_share_federal)

        return incentives
