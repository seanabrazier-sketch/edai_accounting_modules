from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oklahoma')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['High-level category'] == 'Manufacturing') +
            (self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services') +
            (self.project_level_inputs['Project category'] == 'R&D Center')) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                        property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                      * self.state_local_sales_tax]

        for i in range(1, 11):
            incentives.append((self.pnl.npv_dicts['Annual capital expenditures'][i])
                              * self.state_local_sales_tax)
        if ((self.project_level_inputs['High-level category'] == 'Manufacturing') and
                ((((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                      property_type=RealProperty.CONSTRUCTION_MATERIAL) >= 5000000) and
                   (self.project_level_inputs['Promised jobs'] >= 100)) or
                  (((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                       property_type=RealProperty.CONSTRUCTION_MATERIAL) >= 1000000)) and
                   (self.project_level_inputs['Promised jobs'] >= 75)) or
                  (((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                       property_type=RealProperty.CONSTRUCTION_MATERIAL) >= 300000000)) and
                   (self.project_level_inputs['Promised jobs'] >= 1750))))):

            incentives[0] = incentives[0] + (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                               property_type=RealProperty.CONSTRUCTION_MATERIAL)
                                             * self.state_local_sales_tax)

        return incentives
