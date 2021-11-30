from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Texas')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = special_localities_df['Zone Type 3']['Angelina County, TX']
        self.min_jobs_urban = 75
        self.min_jobs_rural = 25
        self.bls_wages = kwargs['state_to_prevailing_wages']['Texas']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Texas Enterprise Fund']

    def estimated_eligibility(self) -> bool:
        if ((('Urban' in self.special_localities and self.project_level_inputs['Promised jobs'] >= self.min_jobs_urban)
                and (self.project_level_inputs['Promised jobs'] >= self.min_jobs_rural)) and
                (self.project_level_inputs['Promised wages'] >= self.bls_wages)):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.median_ipj * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
