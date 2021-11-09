from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sig_capital_investment = 'Yes'
        self.min_jobs_man_dist = 15
        self.min_jobs_every = 50
        self.customized_workforce_recruitment = kwargs['workforce_programs_ipj_map']['Customized workforce recruitment']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['High-level category'] == 'Manufacturing' or \
             self.project_level_inputs['Project category'] == 'Distribution center') and
            (self.project_level_inputs['Promised jobs'] >= self.min_jobs_man_dist)) \
                or ((self.project_level_inputs['Project category'] == 'Corporate headquarters'
                     or self.project_level_inputs['Project category'] == 'Distribution center') and
                    (self.project_level_inputs['Promised jobs'] >= self.min_jobs_every)) \
                and \
                (self.project_level_inputs['High-level category'] == 'Manufacturing') + \
                (self.project_level_inputs['Project category'] == 'Corporate headquarters') + \
                (self.project_level_inputs['Project category'] == 'Distribution center') + \
                (self.project_level_inputs['Project category'] == 'R&D center') + \
                (self.project_level_inputs['High-level category'] == 'Information technology') > 0 \
                and self.sig_capital_investment == 'Yes':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.customized_workforce_recruitment * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
