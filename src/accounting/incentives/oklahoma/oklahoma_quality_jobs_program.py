from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oklahoma')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_oos_requirements = 'Yes'
        self.min_health_coverage = 'Yes'
        self.state_specific = 'Yes'
        self.bls_wages = kwargs['state_to_prevailing_wages']['Oklahoma']
        if self.project_level_inputs['IRS Sector'] in naics_master_crosswalk_df['2017 NAICS US Title']:
            value = 'Yes'
        else:
            value = 'No'

    def estimated_eligibility(self) -> bool:
        # inellgible
        if ((self.project_level_inputs['Promised jobs'] >= 10) +
            (self.project_level_inputs['Promised wages'] >= (min(103736, 3 * self.bls_wages))) +
            (self.min_oos_requirements == 'Yes') +
            (self.state_specific == 'Yes')) == 4:
            eligible = 'No'
        else:
            eligible = 'Yes'

        if ((eligible == 'Yes') +
            (self.project_level_inputs['Equivalent payroll (BASE)'] >= 2500000) +
            (self.project_level_inputs['Promised wages'] >= self.bls_wages * 1) +
            (self.state_specific == 'Yes') +
            (self.min_health_coverage == 'Yes') +
            (self.min_oos_requirements == 'Yes')) == 6:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = .05 * self.project_level_inputs['Equivalent payroll (BASE)']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
