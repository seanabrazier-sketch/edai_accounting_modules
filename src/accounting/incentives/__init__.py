from typing import List
class IncentiveProgramBase(object):
    def estimated_eligibility(self)-> bool:
        return False
    def estimated_incentives(self) ->List[float]:
        return []

