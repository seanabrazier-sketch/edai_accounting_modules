from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Wisconsin')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_jobs = 15
        self.cost_to_train_employee = kwargs['workforce_programs_ipj_map']['Customized workforce recruitment']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised jobs'] >= self.min_jobs and \
                (self.project_level_inputs['IRS Sector'] == 'Transportation equipment manufacturing') + \
                (self.project_level_inputs['IRS Sector'] == 'Beverage and tobacco product manufacturing' or \
                 self.project_level_inputs['IRS Sector'] == 'Food manufacturing') + \
                (self.project_level_inputs['IRS Sector'] == 'Information total') + \
                (self.project_level_inputs['High-level category'] == 'Forestry and logging') + \
                (self.project_level_inputs['Project category'] == 'Professional, scientific, and technical services') + \
                (self.project_level_inputs['Rollup IRS sector'] == 'Air, rail, and water transportation') > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.cost_to_train_employee * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:2]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
