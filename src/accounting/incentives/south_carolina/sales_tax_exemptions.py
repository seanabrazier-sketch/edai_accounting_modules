from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_capex = 35000000
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['High-level category'] == 'Manufacturing' or \
                (self.project_level_inputs['Project category'] == 'Distribution Center' and
                 self.project_level_inputs['Promised capital investment'] >= self.min_capex) or \
                self.project_level_inputs['Project category'] == 'R&D Center':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                         property_type=RealProperty.CONSTRUCTION_MATERIAL)
                       * self.state_local_sales_tax)]
        for i in range(1, 11):
            incentives.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)

        return incentives
