from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.multiple_state_rate = 2
        self.corp_tax = self.pnl_inputs['state_corporate_income_tax_rate']
        self.sales_apportionment_df = self.pnl_inputs['state_corporate_income_tax_apportionment']
        self.unemp_rate = float(special_localities_df['UnempRate']['Anderson County, SC'])
        self.unemp_rate_state = kwargs['state_to_unemployment_rate']['South Carolina']
        self.irs_sector = self.project_level_inputs['IRS Sector'].lower()
        self.cogs = irs_is_statements_df.groupby(['number'])[self.irs_sector].sum()[
                        46] / \
                    irs_is_statements_df.groupby(['number'])[self.irs_sector].sum()[33]
        self.sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.rd_spending = self.pnl_inputs['research_and_development_rate']
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
        if (self.project_level_inputs['Promised jobs'] >= 100 or self.project_level_inputs['Promised jobs'] >= 200) and \
                self.unemp_rate >= (self.unemp_rate_state * self.multiple_state_rate):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums1 = [0.0, self.sales_data]
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

        incentives = []
        for i in income_subject_tax:
            incentives.append(self.corp_tax * (i * self.sales_apportionment_df))

        return incentives
