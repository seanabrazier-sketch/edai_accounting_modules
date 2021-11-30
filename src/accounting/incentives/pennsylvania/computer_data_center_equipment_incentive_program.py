from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Pennsylvania')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        #need to fix this population for county user input
        self.population = float(special_localities_df['Population']['Philadelphia County, PA'])
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if self.population >= 250000:
            value = 'Large'
        else:
            value = 'Small'
        #FINISHHHHHH WEDNESDAY - I am certain it is right
        if self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services' or \
                self.project_level_inputs['Equivalent payroll (BASE)'] >= 1000000:
            return False
        else:
            if (value == 'Large') and (self.project_level_inputs['Promised capital investment'] >= 50000000):
                return True
            else:
                if (value == 'Small') and (self.project_level_inputs['Promised capital investment'] >= 25000000):
                    return True
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                        property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                      * self.state_local_sales_tax]

        for i in range(1, 11):
            incentives.append((self.pnl.npv_dicts['Annual capital expenditures'][i])
                              * self.state_local_sales_tax)
        return incentives



