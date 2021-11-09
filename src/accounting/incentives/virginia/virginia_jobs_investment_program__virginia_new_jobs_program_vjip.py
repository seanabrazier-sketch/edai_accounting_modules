from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_wages_fed = 1.35
        self.fte_greater_250 = "Yes"
        self.min_jobs = 25
        self.min_cap_investment = 1000000
        self.min_jobs_small_business = 5
        self.min_cap_investment_small_business = 100000
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Virginia Jobs Investment Program']

    def estimated_eligibility(self) -> bool:
        if (self.project_level_inputs['Promised wages'] / 2080 >= self.min_wages_fed) \
                + (
                (self.fte_greater_250 == "Yes") + (self.project_level_inputs['Promised jobs'] >= self.min_jobs) +
                 (self.project_level_inputs['Promised capital investment'] >= self.min_cap_investment) == 3) \
                + (
                (self.project_level_inputs['Promised jobs'] >= self.min_jobs_small_business) + (self.project_level_inputs[
                      'Promised capital investment'] >= self.min_cap_investment_small_business) == 2) \
                + (
                (self.project_level_inputs['High-level category'] == 'Manufacturing') +
                (self.project_level_inputs['Project category'] == 'Corporate headquarters') +
                (self.project_level_inputs['Project category'] == 'Distribution center') +
                (self.project_level_inputs['Project category'] == 'R&D center') +
                (self.project_level_inputs['High-level category'] == 'Information technology') > 0) \
                >= 3:
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
