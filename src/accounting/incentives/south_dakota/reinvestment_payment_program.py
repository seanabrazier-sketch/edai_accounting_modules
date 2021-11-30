from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Dakota')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_investment = 20000000
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['South Dakota Reinvestment Program']

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised capital investment'] >= self.min_investment:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = min((self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                      property_type=RealProperty.CONSTRUCTION_MATERIAL)
                                                    +
                                                    self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                      property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                                                    +
                                                    self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                      property_type=PersonalProperty.FIXTURES)
                                                    ))
                     , (self.median_ipj * self.project_level_inputs['Promised jobs']))
        incentives = [0.0, output]
        for j in range(1, 2):
            if len(incentives[2:]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)

        output2 = self.median_ipj * self.project_level_inputs['Promised jobs']
        for j in range(1, 9):
            if len(incentives) + 1 >= 1:
                incentives.append('-')
            else:
                incentives.append(output2)
        return incentives
