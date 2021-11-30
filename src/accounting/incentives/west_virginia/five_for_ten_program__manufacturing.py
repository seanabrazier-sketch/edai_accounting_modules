from accounting.incentives import *
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType
from accounting.data_store import *
from itertools import repeat


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.hundred_mil_in_place = False
        self.capex = kwargs['capex']
        self.property_tax = self.pnl_inputs['property_tax_rate']
        self.real_personal_property = .95

    def estimated_eligibility(self) -> bool:
        # come back to this one because one of the requirement cells on excel did not reference one of the no's
        if self.project_level_inputs['Attraction or Expansion?'] == 'Expansion' \
                and self.project_level_inputs['Promised capital investment'] >= 50000000 \
                and self.hundred_mil_in_place == True:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        num = [0.0]
        num.extend(repeat((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=RealProperty.LAND) +
                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=PersonalProperty.FIXTURES)) * self.property_tax, 10))
        incentives = []
        for i in num:
            incentives.append(i * self.real_personal_property)

        return incentives
