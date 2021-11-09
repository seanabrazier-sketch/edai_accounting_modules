from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Wisconsin')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = special_localities_df['Zone Type 2']['Adams County, WI']
        self.max_per_job = 5000
        self.reimburse_training_all_counties = .50
        self.reimburse_training_rural_county = .75
        self.cost_to_train_employee = kwargs['workforce_programs_ipj_map']['Costs to train employee']
        #self.user_input = grant_estimates_misc_df['Amount']['Costs to train employee'] #Not sure if correct


    def estimated_eligibility(self) -> bool:
        return True


    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]

        if self.special_localities == 'Designated rural county':
            incentives.append(min(self.max_per_job, int(self.reimburse_training_rural_county
                                                        * self.cost_to_train_employee))
                              * self.project_level_inputs['Promised jobs'])

        for i in range(1, 10):
            incentives.append(0.0)

        return incentives
