from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.cost_to_train_employee = kwargs['workforce_programs_ipj_map']['Costs to train employee'] / 2

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised wages'] >= 10.5 * 1.5:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = min((self.cost_to_train_employee * self.project_level_inputs['Promised jobs'])
                     , (5000/2*self.project_level_inputs['Promised jobs']))
        incentives = [0.0] * 11
        incentives[1] = output
        incentives[2] = output
        return incentives
