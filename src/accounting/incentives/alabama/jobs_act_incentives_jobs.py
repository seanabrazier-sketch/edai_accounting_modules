from accounting.incentives import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        pass

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        return [200000.0]
