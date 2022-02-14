from accounting.incentives import *
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType
from accounting.data_store import *
from itertools import repeat


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.capex = kwargs['capex']
        self.tax_credit = .10


    def estimated_eligibility(self) -> bool:
        if 15 <= self.project_level_inputs['Promised jobs'] < 20 \
                and self.project_level_inputs['Project category'] == 'Corporate headquarters':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        num = [0.0]
        num.extend(repeat((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                           self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                             property_type=PersonalProperty.FIXTURES)) / self.tax_credit, 10))

        incentives = [0.0, num[1]]
        for j in range(1, 10):
            if len(incentives) + 1 >= 13:
                incentives.append(0)
            else:
                incentives.append(num[j])

        return incentives
