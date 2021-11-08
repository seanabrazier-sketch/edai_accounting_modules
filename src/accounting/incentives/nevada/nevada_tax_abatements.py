from accounting.incentives import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_type = kwargs['project_level_inputs']['Project type']
        # assume Urban
        self.geography = 'Urban'
        self.is_manufacturing = kwargs['project_level_inputs']['High-level category'] == 'Manufacturing'
        self.is_data_center = kwargs['project_level_inputs']['IRS Sector'] == 'Data processing, hosting, and related services'
        self.is_aviation_manufacturing = kwargs['project_level_inputs']['IRS Sector'] == 'Transportation equipment manufacturing'
        self.sales_tax_rate = kwargs['pnl_inputs']['state_local_sales_tax_rate']

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        incentives = list()

        return incentives
