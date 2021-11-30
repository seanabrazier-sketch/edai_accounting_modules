
from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oregon')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Oregon Strategic Reserve Fund']

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0] * 11
        incentives[1] = self.median_ipj * self.project_level_inputs['Promised jobs']

        return incentives
