from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Utah')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.pnl = kwargs['pnl']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.irs_sector = self.project_level_inputs['IRS Sector'].lower()
        self.special_localities = special_localities_df['Zone Type 1']['Beaver County, UT']
        self.wages_share = 1.1
        self.bls_wages = kwargs['state_to_prevailing_wages']['Utah']
        self.utah_sector = ''
        self.state_revenue = .30
        self.rd_spending = self.pnl_inputs['research_and_development_rate']
        self.withholding_taxes = .0495
        self.estimated_revenue = [self.project_level_inputs['Promised jobs'] * self.project_level_inputs \
            ['Promised wages'] * self.withholding_taxes] * 10
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.state_corporate_income_tax_apportionment = self.pnl_inputs['state_corporate_income_tax_apportionment']
        self.state_corporate_income_tax_rate = self.pnl_inputs['state_corporate_income_tax_rate']
        self.sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.cogs = irs_is_statements_df.groupby(['number'])[self.irs_sector].sum()[
                        46] / \
                    irs_is_statements_df.groupby(['number'])[self.irs_sector].sum()[33]
        self.salaries_wages = \
            irs_is_statements_df.groupby(['number'])[self.irs_sector].sum()[48] / \
            irs_is_statements_df.groupby(['number'])[
                self.irs_sector].sum()[33]

        self.adjuster = self.pnl_inputs['salaries_and_wages_adjuster']

        self.above_line_costs = ((irs_is_statements_df.groupby(['number'])[
                                      self.irs_sector].sum()[47] /
                                  irs_is_statements_df.groupby(['number'])[
                                      self.irs_sector].sum()[33])
                                 +
                                 (irs_is_statements_df.groupby(['number'])[
                                      self.irs_sector].sum()[50] /
                                  irs_is_statements_df.groupby(['number'])[
                                      self.irs_sector].sum()[33])) - self.rd_spending

    def estimated_eligibility(self) -> bool:
        # this needs to be fixed for the p&L IRS data... !!!
        if (((self.special_localities == 'Urban' and self.project_level_inputs['Promised jobs'] >= 50)
             and (self.special_localities == 'Rural')) and (self.project_level_inputs['Promised wages'] >=
                                                            self.bls_wages * self.wages_share) and self.utah_sector > 0):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums1 = [self.sales_data]
        for i in range(1, 10):
            nums1.append(nums1[-1] * (1 + self.project_level_inputs['Inflation (employment cost index)']))

        nums2 = []
        for i in nums1:
            nums2.append(i * self.cogs)

        nums3 = []
        for i, j in zip(nums1, nums2):
            nums3.append(i - j)

        nums4 = []
        if self.project_level_inputs['P&L Salary state adjuster (on/off)'] == 'IRS_AdjByState':
            for i in nums1:
                nums4.append(i * self.salaries_wages * self.adjuster)
        elif self.project_level_inputs['P&L Salary state adjuster (on/off)'] == 'IRS_NoAdj':
            for i in nums1:
                nums4.append(i * self.salaries_wages)
        elif self.project_level_inputs['P&L Salary state adjuster (on/off)'] == 'GivenWages':
            nums4.append(self.project_level_inputs['Promised wages'] /
                         self.project_level_inputs['Wages as share of total compensation (manuf. vs. services)']
                         * self.project_level_inputs['Promised jobs'])
            for i in range(1, 9):
                nums4.append(nums4.append((self.project_level_inputs['Promised wages'] /
                                           self.project_level_inputs[
                                               'Wages as share of total compensation (manuf. vs. services)']
                                           * self.project_level_inputs['Promised jobs'])) * (
                                     1 + self.project_level_inputs['Inflation (employment cost index']))
        nums5 = []
        for i in nums1:
            nums5.append(i * self.rd_spending)

        nums6 = []
        for i in nums1:
            nums6.append(i * self.above_line_costs)

        income_subject_tax = []
        for i, j, k, l in zip(nums3, nums4, nums5, nums6):
            income_subject_tax.append(i - (j + k + l))

        nums8 = []
        for i in income_subject_tax:
            nums8.append(i * self.state_corporate_income_tax_rate * self.state_corporate_income_tax_apportionment)

        nums9 = []
        for i in range(1,11):
            nums9.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)

        nums10 = []
        for i, j in zip(nums8, nums9):
            nums10.append(i + j)

        nums11 = []
        for i, j in zip(nums10, self.estimated_revenue):
            nums11.append(i + j)

        incentives = []
        for i in nums11:
            incentives.append(i * self.state_revenue)

        return incentives
