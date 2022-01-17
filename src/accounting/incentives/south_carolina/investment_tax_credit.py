import statistics

from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        benefits = [.005, .01, .015, .02, .025]
        output = statistics.mean(benefits) * self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                               property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
        incentives = [0.0] * 11
        incentives[1] = output

        return incentives
