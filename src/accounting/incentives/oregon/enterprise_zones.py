from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oregon')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.property_tax = self.pnl_inputs['property_tax_rate']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        output = (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.LAND) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.FIXTURES)) * self.property_tax

        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:]) + 1 >= 4:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
