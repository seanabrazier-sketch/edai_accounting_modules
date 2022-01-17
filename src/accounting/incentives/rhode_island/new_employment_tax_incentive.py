from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.max_payout = 2400

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        output = (min(self.max_payout, self.project_level_inputs['Promised wages'] * .40)
                  * self.project_level_inputs['Promised jobs'])
        incentives = [0.0] * 11
        incentives[2] = output

        return incentives
