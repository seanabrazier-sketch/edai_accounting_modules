from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.bls_wages = kwargs['state_to_prevailing_wages']['Rhode Island']
        self.rhode_island_high_performance = 'High performance'
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        # this needs to be fixed for the p&L IRS data... !!!

        if self.project_level_inputs['High-level category'] == 'Manufacturing' and \
                self.rhode_island_high_performance == 'High performance' and \
                self.project_level_inputs['Promised wages'] >= (self.bls_wages * 1.25):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = .10 * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                          property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                        (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                           property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                         (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                            property_type=PersonalProperty.FIXTURES))))
        incentives = [0.0] * 11
        incentives[1] = output
        return incentives

