from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.property_tax_rate = self.pnl_inputs['property_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['High-level category'] == 'Manufacturing') +
            (self.project_level_inputs['Project category'] == 'Corporate Headquarters') +
            (self.project_level_inputs['Project category'] == 'Distribution Center') > 0) \
                and (self.project_level_inputs['Promised jobs'] >= 75) \
                and (self.project_level_inputs['Promised capital investment'] >= 50000):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = ((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.LAND) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.FIXTURES)) * self.property_tax_rate) * .35

        #benefit range
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
