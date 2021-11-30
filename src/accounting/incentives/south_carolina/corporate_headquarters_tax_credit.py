from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Rhode Island')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        eligible = []
        if self.project_level_inputs['Project category'] == 'Corporate headquarters' \
                and self.project_level_inputs['Promised jobs'] >= 75:
            eligible.append('Yes')
        else:
            eligible.append('No')

        if ((self.project_level_inputs['Project category'] == 'Corporate headquarters' or
             self.project_level_inputs['Project category'] == 'R&D Center') and
                (self.project_level_inputs['Promised jobs'] >= 40) and (eligible == 'No')):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = .20 * ((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                           property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                         (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                            property_type=RealProperty.LAND))))
        incentives = [output] * 11
        incentives[0] = 0.0

        return incentives
