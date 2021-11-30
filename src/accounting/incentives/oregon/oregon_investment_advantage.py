from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oregon')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = special_localities_df['Zone Type 1']['Benton County, OR']
        self.corp_tax = self.pnl_inputs['state_corporate_income_tax_rate']
        self.gross_receipts_tax_rate = self.pnl_inputs['gross_receipts_tax_rate']
        self.irs_sector = self.project_level_inputs['IRS Sector'].lower()
        self.sales_apportionment_df = self.pnl_inputs['state_corporate_income_tax_apportionment']
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
        #come back to this!!!!
        if ((self.special_localities == 'Investment Advantage eligible') +
                (self.project_level_inputs['Promised jobs'] >= 5) +
                (self.project_level_inputs['Promised wages'] >= (1 * 1)) +
                (2 == 2)) == 4:
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

        nums6 = []
        for i in income_subject_tax:
            nums6.append((self.corp_tax * (i * self.sales_apportionment_df)))

        nums7 = []
        for i, j in zip(nums1, nums6):
            nums7.append((i * self.gross_receipts_tax_rate) + j)

        incentives = []
        for i in nums7:
            if len(incentives[1:]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(i)

        return incentives
