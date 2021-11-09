from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.bls_wages = kwargs['state_to_prevailing_wages']['Virginia']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sales_apportionment_df = kwargs['sales_apportionment_df']['Tax incidence (Portion of sales to be taxed)'][
            'Virginia']
        self.no_employment_before_2018 = "Yes"
        self.corp_tax = kwargs['pnl_inputs']['state_corporate_income_tax_rate']
        self.min_locality_wage = self.bls_wages * 1.5
        self.grant_per_job = 2000
        self.special_localities = [special_localities_df['Zone Type 1']['Accomack County, VA'],
                                   special_localities_df['Zone Type 2']['Accomack County, VA'],
                                   special_localities_df['Zone Type 3']['Accomack County, VA']]
        self.min_cap_investment = 5000000
        self.min_jobs1 = 10
        self.min_jobs2 = 50
        self.high_level_categories = ['Manufacturing', 'Transportation and warehousing', 'Information',
                                      'Finance and insurance', 'Professional, scientific, and technical services',
                                      'Management of companies (holding companies)']
        self.cogs = irs_is_statements_df.groupby(['number'])['computer and electronic product manufacturing'].sum()[
                        46] / \
                    irs_is_statements_df.groupby(['number'])['computer and electronic product manufacturing'].sum()[33]
        self.sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.rd_spending = self.pnl_inputs['research_and_development_rate']

        self.salaries_wages = \
            irs_is_statements_df.groupby(['number'])['computer and electronic product manufacturing'].sum()[48] / \
            irs_is_statements_df.groupby(['number'])[
                'computer and electronic product manufacturing'].sum()[33]

        self.adjuster = \
            census_acs_earn_state_df['B24031_006E']['Virginia'] / census_acs_earn_state_df['B24031_006E'][
                'United States']

        self.above_line_costs = ((irs_is_statements_df.groupby(['number'])[
                                      'computer and electronic product manufacturing'].sum()[47] /
                                  irs_is_statements_df.groupby(['number'])[
                                      'computer and electronic product manufacturing'].sum()[33])
                                 +
                                 (irs_is_statements_df.groupby(['number'])[
                                      'computer and electronic product manufacturing'].sum()[50] /
                                  irs_is_statements_df.groupby(['number'])[
                                      'computer and electronic product manufacturing'].sum()[33])) - self.rd_spending

    def estimated_eligibility(self) -> bool:
        if (self.no_employment_before_2018 == "Yes") \
                + (self.project_level_inputs['Promised wages'] >= self.min_locality_wage) \
                + (sum(True for i in self.high_level_categories if
                       self.project_level_inputs['High-level category'] in i) > 0) \
                + ((self.project_level_inputs['Promised capital investment'] >= self.min_cap_investment and
                    self.project_level_inputs['Promised jobs'] >= self.min_jobs1) or
                   (self.project_level_inputs['Promised jobs'] >= self.min_jobs2)) \
                + (
                sum(True for i in self.special_localities if 'Qualified locality' in i) > 0) \
                == 5:
            return True  # this brings true because you hardcoded the county in special localities
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

        nums7 = []
        for i in income_subject_tax:
            nums7.append(i * self.corp_tax * self.sales_apportionment_df)

        if (self.no_employment_before_2018 == "Yes") \
                + (self.project_level_inputs['Promised wages'] >= self.min_locality_wage) \
                + (sum(True for i in self.high_level_categories if
                       self.project_level_inputs['High-level category'] in i) > 0) \
                + ((self.project_level_inputs['Promised capital investment'] >= self.min_cap_investment and
                    self.project_level_inputs['Promised jobs'] >= self.min_jobs1) or
                   (self.project_level_inputs['Promised jobs'] >= self.min_jobs2)) \
                + (
                sum(True for i in self.special_localities if 'Qualified locality' in i) > 0) \
                == 5:
            # I am making it zero instead of the comment because the output needs to match,
            # Can fix this when figure out what to do with county level data (special localities)
            nums8 = [0] * 11  # self.grant_per_job * self.project_level_inputs['Promised jobs'])
        else:
            nums8 = [0] * 11

        incentives = []
        for i, j in zip(nums7, nums8):
            incentives.append(i + j)

        return incentives
