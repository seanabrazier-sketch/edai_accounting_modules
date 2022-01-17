from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Tennessee')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_sq_ft = 'Yes'
        self.min_jobs = 20
        self.prevailing_wages_state = kwargs['state_to_prevailing_wages']['Texas']
        # Default to state value
        self.bls_wages = kwargs['county_to_prevailing_wages'].get(self.county, self.prevailing_wages_state)
        self.min_county_wages = 1.2
        self.min_cap_investment = 200000000
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services')
                + (self.min_sq_ft == 'Yes')
                + (self.project_level_inputs['Promised jobs'] >= self.min_jobs)
                + (self.project_level_inputs['Promised wages'] >= (self.bls_wages * self.min_county_wages))
                + (self.project_level_inputs['Promised capital investment'] >= self.min_cap_investment) == 5):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:

        incentives = [self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                      property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                                                    )]
        for i in range(1, 11):
            incentives.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)

        return incentives
