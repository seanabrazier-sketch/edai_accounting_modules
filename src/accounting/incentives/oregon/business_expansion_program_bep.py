
from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oregon')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sector_df = ['Manufacturing', 'Information', 'Wholesale trade',
                          'Finance and insurance', 'Transportation and warehousing',
                          'Professional, scientific, and technical services']
        self.fte = 'Yes'
        self.bls_wages = kwargs['state_to_prevailing_wages']['Oregon']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['Promised jobs'] >= 50) +
                (self.fte == 'Yes') +
                (self.project_level_inputs['Promised wages'] >= self.bls_wages * 1.5) +
                any(self.project_level_inputs['High-level category'] in item for item in self.sector_df)) == 4:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0] * 11
        incentives[1] = (self.project_level_inputs['Promised jobs'] * self.project_level_inputs['Promised wages'] * .09
                         + self.project_level_inputs['Promised jobs'] * self.project_level_inputs['Promised wages'] * .09)
        return incentives
