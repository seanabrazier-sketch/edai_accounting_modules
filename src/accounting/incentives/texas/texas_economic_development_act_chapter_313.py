from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Texas')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.bls_wages = kwargs['state_to_prevailing_wages']['Texas']
        self.min_county_wages = 1.1
        # just hardcode this for now until you find data:
        self.min_county_capex = 28886501
        self.property_tax = self.pnl_inputs['property_tax_rate']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['Promised wages'] >= (self.bls_wages * self.min_county_wages))
                and (self.project_level_inputs['Promised capital investment'] >= self.min_county_capex)):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.property_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                        property_type=RealProperty.LAND) +
                                      self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                        property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                                      self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                        property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                                      self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                        property_type=PersonalProperty.FIXTURES))
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
