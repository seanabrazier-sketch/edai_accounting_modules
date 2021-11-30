from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Project category'] == 'Corporate headquarters' and \
                self.project_level_inputs['Promised jobs'] >= 75:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = .20 * ((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                           property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                         (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                            property_type=PersonalProperty.FIXTURES))))
        incentives = [0.0, output]

        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 85:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
