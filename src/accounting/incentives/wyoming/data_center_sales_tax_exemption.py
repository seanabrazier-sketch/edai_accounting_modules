from accounting.incentives import *
from util.capex import SHARES_INDUSTRIAL, RealProperty, PersonalProperty, IndustryType
from accounting.data_store import *
from itertools import repeat


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Wyoming')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.pnl = kwargs['pnl']
        self.project_level_inputs = kwargs['project_level_inputs']
        # self.promised_capital_investment = self.project_level_inputs['Promised capital investment']
        self.capex = kwargs['capex']
        self.tier1_min_capex_structure = 5000000
        self.tier2_min_capex_structure = 2000000
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.depreciation_building = 40
        self.depreciation_personal_prop = 5

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services' \
                and (self.capex.amount(
            industry_type=self.pnl_inputs['industry_type'],
            property_type=RealProperty.CONSTRUCTION_MATERIAL
        )) >= self.tier1_min_capex_structure:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))]
        for i in range(1, 11):
            nums.append(self.pnl.npv_dicts['Annual capital expenditures'][i])

        incentives = []
        for i in nums:
            if i >= self.tier2_min_capex_structure:
                incentives.append(i * self.state_local_sales_tax)
            else:
                0

        return incentives
