from accounting.incentives import *
from accounting.data_store import *
import numpy as np


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Tennessee')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.bls_wages = kwargs['state_to_prevailing_wages']['Tennessee']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Tennessee FastTrack Economic Development Grant']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised wages'] >= self.bls_wages:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.project_level_inputs['Promised jobs'] * np.mean([4287, 5798, 4269, 4249])
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)

        output2 = self.median_ipj * self.project_level_inputs['Promised jobs']
        incentives2 = [0.0, output2]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 1:
                incentives2.append(0)
            else:
                incentives2.append(output2)

        incentives = [incentives] + [incentives2]

        return incentives
