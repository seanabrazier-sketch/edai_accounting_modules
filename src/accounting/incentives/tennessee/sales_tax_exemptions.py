from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Tennessee')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['High-level category'] == 'Manufacturing')
            + (self.project_level_inputs['Project category'] == 'Corporate Headquarters')
            + (self.project_level_inputs['Project category'] == 'R&D Center')
            + (self.project_level_inputs['Project category'] == 'Call Center')
            + (self.project_level_inputs['Project category'] == 'Distribution Center')
            + (self.project_level_inputs[
                   'IRS Sector'] == 'Data processing, hosting, and related services')) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) * self.state_local_sales_tax)]
        for i in range(1, 11):
            nums.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)

        incentives = []
        for i in nums:
            if ((self.project_level_inputs['High-level category'] == 'Manufacturing')
                + (self.project_level_inputs['Project category'] == 'Corporate Headquarters')
                + (self.project_level_inputs['Project category'] == 'R&D Center')
                + (self.project_level_inputs['Project category'] == 'Call Center')
                + (self.project_level_inputs['Project category'] == 'Distribution Center')
                + (self.project_level_inputs[
                       'IRS Sector'] == 'Data processing, hosting, and related services')) > 0:
                if self.project_level_inputs['Project category'] == 'Corporate Headquarters':
                    incentives.append((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                         property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                                       self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                         property_type=PersonalProperty.FIXTURES))
                                      * .065)
                else:
                    incentives.append(i)

        return incentives
