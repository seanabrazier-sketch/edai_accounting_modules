from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Vermont')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Vermont Employment Growth Incentive']
        self.min_wage = 11.75
        self.percentage = 1.5
        self.incentives_paid_out_yrs = 9
    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised wages']/2080 >= self.min_wage * self.percentage:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentive = []
        output = (self.median_ipj/self.incentives_paid_out_yrs) * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 9:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives



