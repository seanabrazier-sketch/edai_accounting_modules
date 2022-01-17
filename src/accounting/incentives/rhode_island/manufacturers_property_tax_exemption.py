from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.smart_asset_share = .01226 / (.01226 + .01657)
        self.capex = kwargs['capex']
        self.property_tax = self.pnl_inputs['property_tax_rate']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                       * self.smart_asset_share
                       * self.property_tax)] * 11
        incentives[0] = 0.0
        return incentives
