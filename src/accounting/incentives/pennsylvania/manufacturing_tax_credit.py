from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Pennsylvania')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Equivalent payroll (BASE)'] >= 1000000 and \
                self.project_level_inputs['High-level category'] == 'Manufacturing':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0] * 11
        incentives[1] = self.project_level_inputs['Equivalent payroll (BASE)'] * .05

        return incentives
