import statistics

from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.rd_spending = self.pnl_inputs['research_and_development_rate']
        self.sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        nums1 = [0.0, self.sales_data]
        for i in range(1, 10):
            nums1.append(nums1[-1] * (1 + self.project_level_inputs['Inflation (employment cost index)']))

        nums2 = []
        nums3 = []
        for i in nums1:
            nums2.append(i * self.rd_spending)
        for i in nums2[:4]:
            nums3.append(i * .05)

        calculations1 = pd.Series(nums2[1:])
        calculations1 = list(calculations1.rolling(3).mean())
        calculations1 = calculations1[3 - 1:]
        del calculations1[-1]

        fed_base_amount = []
        for i in calculations1:
            fed_base_amount.append(.50 * i)

        excess_fed_base_amount = []
        for i, j in zip(nums2[4:], fed_base_amount):
            excess_fed_base_amount.append(i - j)

        calc1 = []
        for i in excess_fed_base_amount:
            calc1.append(.225 * min(i, 111111))

        calc2 = []
        for i in excess_fed_base_amount:
            calc2.append((i - 111111) * .169)

        incentives = nums3
        for i, j in zip(calc1, calc2):
            incentives.append(i + j)

        return incentives
