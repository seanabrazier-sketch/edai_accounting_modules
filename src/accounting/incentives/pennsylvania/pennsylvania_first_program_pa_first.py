from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Pennsylvania')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['PA First']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised wages']/2080 >= 1.5 * self.project_level_inputs['Federal minimum wage'] \
                and self.project_level_inputs['Promised jobs'] >= 100:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums1 = self.project_level_inputs['Promised capital investment'] / (self.median_ipj * self.project_level_inputs['Promised jobs'])
        incentives = [0.0] * 11
        if nums1 >= 10:
            incentives[1] = self.median_ipj * self.project_level_inputs['Promised jobs']
        else:
            incentives[1] = self.project_level_inputs['Promised capital investment'] * 10

        return incentives
