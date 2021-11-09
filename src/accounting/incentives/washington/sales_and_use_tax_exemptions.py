from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Washington')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.data_center_min = "Yes"
        self.pnl = kwargs['pnl']
        self.special_localities = special_localities_df['Zone Type 1']['Adams County, WA']
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if (self.project_level_inputs['Project category'] == 'Distribution center' and self.data_center_min == "Yes") or \
                self.project_level_inputs['High-level category'] == 'Manufacturing' or \
                self.project_level_inputs['Project category'] == 'R&D Center' or \
                (self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services') \
                + (self.special_localities == 'Rural') + (self.data_center_min == "Yes") == 3:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [self.state_local_sales_tax *
                      (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))]

        for i in range(1, 11):
            incentives.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)

        return incentives
