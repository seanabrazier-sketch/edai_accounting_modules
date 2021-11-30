from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
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
        for i in nums1:
            nums2 = [i * self.rd_spending]
            for j in nums2:
                incentives.append(j * .05)

        return incentives
