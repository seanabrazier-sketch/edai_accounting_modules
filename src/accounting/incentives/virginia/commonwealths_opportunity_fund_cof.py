from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.bls_wages = kwargs['state_to_prevailing_wages']['Virginia']
        self.requirements_list_min_jobs = [50, 25, 25, 25, 15]
        self.requirements_list_min_capex = [5000000, 100000000, 5000000, 25000000, 1500000]
        self.requirements_list_min_avg_wage = [1.0, 1.0, 2.0, .85, .85]
        self.requirements_list_geo = ['n/a', 'n/a', 'n/a', 'No', 'No']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Commonwealth Opportunity Fund']

    def estimated_eligibility(self) -> bool:
        if (((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[0])
             + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[0]
                * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                     >= self.requirements_list_min_capex[0]) == 3)
            + ((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[1])
               + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[1]
                  * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                       >= self.requirements_list_min_capex[1]) == 3)
            + ((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[2])
               + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[2]
                  * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                       >= self.requirements_list_min_capex[2]) == 3)
            + + ((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[3])
                 + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[3]
                    * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                         >= self.requirements_list_min_capex[3])
                 + (self.requirements_list_geo[3] == 'Yes') == 4)
            + + ((self.project_level_inputs['Promised jobs'] >= self.requirements_list_min_jobs[4])
                 + (self.project_level_inputs['Promised wages'] >= self.requirements_list_min_avg_wage[4]
                    * self.bls_wages) + (self.project_level_inputs['Promised capital investment']
                                         >= self.requirements_list_min_capex[4])
                 + (self.requirements_list_geo[4] == 'Yes') == 4)) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0] * 11
        incentives[1] = self.median_ipj * self.project_level_inputs['Promised jobs']
        return incentives

