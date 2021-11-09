from accounting.incentives import *
from accounting.data_store import *
import statistics

class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Washington')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Washington Governor Strategic Reserve Fund']
        #self.discretionary_incentives_group = kwargs['discretionary_incentives_groups']
        self.annual_max = 3000000

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        output = min((self.median_ipj * self.project_level_inputs['Promised jobs']), self.annual_max)
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:2]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
