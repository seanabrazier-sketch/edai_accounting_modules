from accounting.incentives import *
from itertools import repeat

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.num_will_change = 694


    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0, self.project_level_inputs['Promised jobs'] * self.num_will_change]
        incentives.extend(repeat(0.0, 9))

        return incentives
