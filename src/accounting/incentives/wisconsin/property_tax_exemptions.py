from accounting.incentives import *
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.pnl = kwargs['pnl']
        self.capex = kwargs['capex']
        self.property_tax = self.pnl_inputs['property_tax_rate']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services' \
                or self.project_level_inputs['High-level category'] == 'Manufacturing':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = ['BASE YEAR']
        for i in range(1, 11):
            incentives.append((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                 property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))
                              * self.property_tax)

        return incentives
