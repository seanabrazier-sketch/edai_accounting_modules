from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Pennsylvania')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.located = 'No'
        self.capex = kwargs['capex']
        self.sales = self.pnl_inputs['sales']

    def estimated_eligibility(self) -> bool:
        if self.located == 'Yes' and ((self.project_level_inputs['Attraction or Expansion?'] == 'Relocation')
                                      and (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                             property_type=RealProperty.LAND) +
                                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                             property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                             property_type=PersonalProperty.FIXTURES)) >=
                                      (.10 * self.sales)):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0] * 11
        if self.located == 'Yes' and ((self.project_level_inputs['Attraction or Expansion?'] == 'Relocation')
                                      and (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                             property_type=RealProperty.LAND) +
                                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                             property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                             property_type=PersonalProperty.FIXTURES)) >=
                                      (.10 * self.sales)):
            incentives[1] = 59000
        else:
            incentives[1] = 0.0

        return incentives
