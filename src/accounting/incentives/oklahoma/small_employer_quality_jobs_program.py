
from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oklahoma')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        output = .05 * self.project_level_inputs['Equivalent payroll (BASE)']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:]) + 1 >= 7:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
