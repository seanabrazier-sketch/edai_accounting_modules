from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Pennsylvania')
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

        incentives = []
        for i in nums1[:4]:
            incentives.append((i * self.rd_spending) * .06)

        nums3 = []
        for i in nums1:
            nums3.append(i * self.rd_spending)
        calculations1 = pd.Series(nums3[1:])
        calculations1 = list(calculations1.rolling(3).mean())
        calculations1 = calculations1[3 - 1:]
        del calculations1[-1]

        for i, j in zip(nums3[4:], calculations1):
            incentives.append((i - (j * .5)))

        return incentives
