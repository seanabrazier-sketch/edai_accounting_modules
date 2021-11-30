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
        if (self.project_level_inputs['High-level category'] == 'Manufacturing' or
                self.project_level_inputs['High-level category'] == 'Information') and \
                (self.project_level_inputs['Attraction or Expansion?'] == 'Relocation'):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums1 = [0.0, self.sales_data]
        for i in range(1, 10):
            nums1.append(nums1[-1] * (1 + self.project_level_inputs['Inflation (employment cost index)']))

        nums2 = [y - x for x, y in zip(nums1, nums1[1:])]
        del nums2[0]
        nums2.insert(0, 0.0)
        nums2.insert(0, 0.0)

        incentives = [0.0] * 11
        incentives[3] = min(nums2[2] * .5, 100000)
        incentives[4] = min(nums2[3] * .5, 100000)

        return incentives
