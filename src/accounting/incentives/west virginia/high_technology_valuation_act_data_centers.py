from accounting.incentives import *
from accounting.incentives import *
from accounting.data_store import *
from itertools import repeat
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.pnl = kwargs['pnl']
        self.real_personal_property = .95
        self.property_tax = self.pnl_inputs['property_tax_rate']
        self.capex = kwargs['capex']
        self.tax_foundation_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        num1 = [0.0]
        calc1 = (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.FIXTURES)) \
                * self.real_personal_property * self.property_tax
        num1.append(calc1)
        num1.extend(repeat(calc1, 9))

        num2 = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))
                * self.tax_foundation_sales_tax]
        for i in range(1, 11):
            num2.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.tax_foundation_sales_tax)

        incentives = []
        for i, j in zip(num1, num2):
            incentives.append(i + j)

        return incentives
