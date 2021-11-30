from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        return [200000.0]
