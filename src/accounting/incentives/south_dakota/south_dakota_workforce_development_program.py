from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Dakota')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_wages_hour = 14.00
        self.benefit_per_worker = 500

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised wages'] >= (self.min_wages_hour*2080):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.benefit_per_worker * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
