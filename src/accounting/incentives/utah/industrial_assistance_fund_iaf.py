from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Utah')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Utah Industrial Assistance Fund'] / 5
        self.max_payout = 250000
        self.max_payout_annual = self.max_payout / 5
        self.locating_ez = 'No'
        self.special_localities = special_localities_df['Zone Type 1']['Cache County, UT'] #fix later
        self.capex = kwargs['capex']
        self.annual_tax_credit = .05

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        output = self.median_ipj * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
