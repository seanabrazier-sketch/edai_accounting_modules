from accounting.incentives import *
from itertools import repeat
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.years = 10
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]
        incentives.extend(repeat((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                    property_type=RealProperty.LAND) +
                                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                    property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                    property_type=PersonalProperty.FIXTURES)) / self.years, 10))

        return incentives
