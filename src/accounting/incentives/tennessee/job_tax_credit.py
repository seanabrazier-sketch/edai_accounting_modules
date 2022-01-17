from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Tennessee')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_jobs = 25
        self.min_jobs2 = 10
        self.min_cap_investment = 500000
        self.comm_resurg_credit = 2500
        # he has not put in the acs industry earn yet so just hardcode for now:
        self.state_avg_occ_wage = 40568 #hardcoded
        self.special_localities = float(special_localities_df['Poverty_x']['Knox County, TN']) #fix later

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised jobs'] >= self.min_jobs and \
                self.project_level_inputs['Promised capital investment'] >= self.min_cap_investment:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        if ((self.project_level_inputs['Promised jobs'] >= self.min_jobs2) +
                (self.project_level_inputs['Promised wages'] >= self.state_avg_occ_wage) +
                (self.special_localities > 30 or self.special_localities == '-') == 3):
            calc = self.comm_resurg_credit + 4500
        else:
            calc = 4500

        output = calc * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
