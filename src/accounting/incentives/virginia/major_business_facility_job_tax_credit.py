from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_jobs = 50
        self.distressed_min_jobs = 25
        self.special_localities = [special_localities_df['Zone Type 1']['Accomack County, VA'],
                                   special_localities_df['Zone Type 2']['Accomack County, VA'],
                                   special_localities_df['Zone Type 3']['Accomack County, VA']]
        self.two_years = 500

    def estimated_eligibility(self) -> bool:
        if (sum(True for i in self.special_localities if 'distressed' in i) > 0 or \
           sum(True for i in self.special_localities if 'Enterprise Zones' in i) > 0 and \
                (self.project_level_inputs['Promised jobs'] >= self.distressed_min_jobs)) or \
                self.project_level_inputs['Promised jobs'] >= self.min_jobs:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.two_years * self.project_level_inputs['Promised jobs']
        # Year 0 = $0 (construction), Year 1 = full credit, Year 2 = full credit,
        # Years 3-10 = $0.  The credit is awarded for two consecutive tax years.
        incentives = [0.0, output]

        for j in range(1, 10):
            if j == 1:   # Year 2 — second year of the two-year credit
                incentives.append(output)
            else:
                incentives.append(0)

        return incentives
