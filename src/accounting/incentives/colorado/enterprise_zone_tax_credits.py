from accounting.incentives import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        reduced_rate = 0.033125
        sales_tax = kwargs['pnl_inputs']['state_local_sales_tax_rate']
        self.savings_from_reduced_rate = sales_tax - reduced_rate
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.pnl = kwargs['pnl']
        self.capex = kwargs['capex']
        self.unemployment_rate = kwargs['state_to_unemployment_rate']['Colorado']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] > 1.25 * self.unemployment_rate \
                or self.project_level_inputs['Project category'] < 0.75 * ():
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = list()
        incentives.append(
            self.capex.amount(
                industry_type=self.pnl_inputs['industry_type'],
                property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT
            ) * self.savings_from_reduced_rate
        )
        for i in range(1, 11):
            incentives.append(
                self.pnl.npv_dicts['Annual capital expenditures'][i]
                * self.savings_from_reduced_rate
            )
        return incentives
