from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.rhode_island_target_industry = 'Target industry'
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Rhode Island Qualified Jobs Incentive Act']

    def estimated_eligibility(self) -> bool:
        # this needs to be fixed for the p&L IRS data... !!!

        if self.rhode_island_target_industry == 'Target industry' and self.project_level_inputs['Promised jobs'] > 200 \
                and self.project_level_inputs['Promised jobs'] >= 100:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.project_level_inputs['Promised jobs'] * self.median_ipj
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
