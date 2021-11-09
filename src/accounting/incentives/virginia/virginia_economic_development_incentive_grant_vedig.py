from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.bls_wages = kwargs['state_to_prevailing_wages']['Virginia']
        self.requirements_list_min_jobs = [400, 300, 200]
        self.requirements_list_min_avg_wage = [1.5, 2.0, 1.5]
        self.requirements_list_min_capex = [5000000, 5000000, 0]
        self.requirements_list_min_capex_job = [6500, 6500, 6500]
        self.requirements_list_geo = ['Yes', 'Yes', 'No']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Virginia Economic Development Incentive Grant (VEDIG)']

    def estimated_eligibility(self) -> bool:
        if (((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[0])
             + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[0]
                * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                     >= self.requirements_list_min_capex[0] or
                                     self.project_level_inputs['Promised capital investment'] /
                                     self.project_level_inputs['Promised jobs']
                                     >= self.requirements_list_min_capex_job[0])
             + (self.requirements_list_geo[0] == 'Yes') == 4)
            + ((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[1])
               + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[1]
                  * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                       >= self.requirements_list_min_capex[1] or
                                       self.project_level_inputs['Promised capital investment'] /
                                       self.project_level_inputs['Promised jobs']
                                       >= self.requirements_list_min_capex_job[1])
               + (self.requirements_list_geo[1] == 'Yes') == 4)
            + ((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[2])
               + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[2]
                  * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                       >= self.requirements_list_min_capex[2] or
                                       self.project_level_inputs['Promised capital investment'] /
                                       self.project_level_inputs['Promised jobs']
                                       >= self.requirements_list_min_capex_job[2])
               + (self.requirements_list_geo[2] == 'Yes') == 4)) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.median_ipj * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
