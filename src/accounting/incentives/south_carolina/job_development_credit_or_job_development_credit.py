from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.prevailing_wages_state = kwargs['state_to_prevailing_wages']['South Carolina']
        # Default to state value
        self.bls_wages = kwargs['county_to_prevailing_wages'].get(self.county, self.prevailing_wages_state)
        self.heath_benefit = 'Yes'
        self.misc_requirements = 'Yes'
        self.withholding_amt = ((self.project_level_inputs['Promised wages'] - 13110) * .07) + 493.06
        self.effective_rate = self.withholding_amt / self.project_level_inputs['Promised wages']

    def estimated_eligibility(self) -> bool:
        if (((self.project_level_inputs['High-level category'] == 'Manufacturing') +
             (self.project_level_inputs['Project category'] == 'Corporate Headquarters') +
             (self.project_level_inputs['Project category'] == 'R&D Center') +
             (self.project_level_inputs['Project category'] == 'Distribution Center') > 0)
            +
            (self.project_level_inputs['Promised jobs'] >= 10)
            +
            (self.project_level_inputs['Promised wages'] >= 1 * self.bls_wages)
            +
            (self.heath_benefit == 'Yes')
            +
            (self.misc_requirements == 'Yes')) == 5:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = min(self.project_level_inputs['Promised jobs'] * self.effective_rate *
                     self.project_level_inputs['Promised wages'], self.project_level_inputs['Promised jobs'] * 3250)
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
