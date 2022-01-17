from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Utah')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['High-level category'] == 'Manufacturing')
                + (self.project_level_inputs['Project category'] == 'R&D Center')
                + (self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services') > 0):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        if self.project_level_inputs['High-level category'] == 'Manufacturing':
            nums1 = [
                self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))]
            for i in range(1, 11):
                nums1.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)
        else:
            nums1 = [0.0] * 11

        if self.project_level_inputs['Project category'] == 'R&D Center':
            nums2 = [
                self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))]
            for i in range(1, 11):
                nums2.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)
        else:
            nums2 = [0.0] * 11
            # this code is not integrated yet so commenting out
            # if life sciences:
            #nums3 = [self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                     #property_type=RealProperty.CONSTRUCTION_MATERIAL))]

        if self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services':
            nums4 = [
                self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT))]
            for i in range(1, 11):
                nums4.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)
        else:
            nums4 = [0.0] * 11

        incentives = []
        for i, j, k in zip(nums1, nums2, nums4):
            incentives.append(i + j + k)

        return incentives
