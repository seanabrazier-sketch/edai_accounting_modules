from accounting.incentives import *
from accounting.data_store import *
from itertools import repeat
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']
        self.tax_foundation_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing' \
                or self.project_level_inputs['Project category'] == 'R&D Center' \
                or self.project_level_inputs['Project category'] == 'Distribution center':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)) * self.tax_foundation_sales_tax]

        for i in range(1, 11):
            incentives.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.tax_foundation_sales_tax)

        return incentives
