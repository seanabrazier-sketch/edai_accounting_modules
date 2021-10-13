from accounting.incentives import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing':

            return True

    def estimated_incentives(self) -> List[float]:
        return [200000.0]
