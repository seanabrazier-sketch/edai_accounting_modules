from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sales_tax = kwargs['pnl_inputs']['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing' or \
                self.project_level_inputs['Project category'] == 'R&D Center':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums = [self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                  property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)]
        for i in range(1, 11):
            nums.append(self.pnl.npv_dicts['Annual capital expenditures'][i])

        incentives = []
        for i in nums:
            incentives.append(i * self.sales_tax)

        return incentives
