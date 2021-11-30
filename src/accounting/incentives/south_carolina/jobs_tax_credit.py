from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('South Carolina')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']
        self.corp_tax = self.pnl_inputs['state_corporate_income_tax_rate']
        self.gross_receipts_tax_rate = self.pnl_inputs['gross_receipts_tax_rate']
        self.property_tax_rate = self.pnl_inputs['property_tax_rate']
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.sales_apportionment_df = self.pnl_inputs['state_corporate_income_tax_apportionment']
        self.state_ui_tax_amount = self.pnl_inputs['state_ui_tax_amount']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = special_localities_df['Zone Type 2']['Anderson County, SC']
        self.bls_wages = kwargs['state_to_prevailing_wages']['South Carolina']
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
        meets = []
        if self.project_level_inputs['High-level category'] == 'Manufacturing':
            meets.append('Yes')
        else:
            meets.append('No')
        if self.project_level_inputs['Project category'] == 'Corporate headquarters':
            meets.append('Yes')
        else:
            meets.append('No')
        if self.project_level_inputs['Project category'] == 'Distribution center':
            meets.append('Yes')
        else:
            meets.append('No')
        if self.project_level_inputs['Project category'] == 'R&D Center':
            meets.append('Yes')
        else:
            meets.append('No')

        # tiers
        if self.special_localities == 1:
            geo_tier = 'Tier 1'
        elif self.special_localities == 2:
            geo_tier = 'Tier 2'
        elif self.special_localities == 3:
            geo_tier = 'Tier 3'
        elif self.special_localities == 4:
            geo_tier = 'Tier 4'
        else:
            geo_tier = 'Tier 1'

        # if qualified service related quality
        # first one is n/a
        if ((geo_tier != 'Tier 4' and self.project_level_inputs['Promised jobs'] >= 25 and
             self.project_level_inputs['Promised wages'] >= (self.bls_wages * 2.5))
            +
            (geo_tier != 'Tier 4' and self.project_level_inputs['Promised jobs'] >= 50 and
             self.project_level_inputs['Promised wages'] >= (self.bls_wages * 2))
            +
            (geo_tier != 'Tier 4' and self.project_level_inputs['Promised jobs'] >= 100 and
             self.project_level_inputs['Promised wages'] >= (self.bls_wages * 1.5))
            +
            (self.project_level_inputs['Promised jobs'] >= 175)
            +
            (geo_tier == 'Tier 4' and
             (self.project_level_inputs['Promised jobs'] >= 10 and geo_tier == 'Tier 4'))) > 0:

            meets.append('Yes')
        else:
            meets.append('No')

        # eligibility
        if ((meets[0] == 'Yes' and self.project_level_inputs['Promised jobs'] >= 10)
            +
            (meets[1] == 'Yes' and self.project_level_inputs['Promised jobs'] >= 10)
            +
            (meets[2] == 'Yes' and self.project_level_inputs['Promised jobs'] >= 10)
            +
            (meets[3] == 'Yes' and self.project_level_inputs['Promised jobs'] >= 10)
            +
            (meets[4] == 'Yes')) > 0:

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

        calc1 = []
        for i in income_subject_tax:
            calc1.append(self.corp_tax * (i * self.sales_apportionment_df))

        calc2 = [self.project_level_inputs['Promised jobs'] * self.state_ui_tax_amount] * 11
        calc2[0] = 0.0

        calc3 = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.FIXTURES)) * self.state_local_sales_tax
                 ]
        for i in range(1, 11):
            calc3.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * self.state_local_sales_tax)

        calc4 = []
        for i in nums1:
            calc4.append(i * self.gross_receipts_tax_rate)

        calc5 = [(self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.LAND) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.FIXTURES)) * self.property_tax_rate] * 11
        calc5[0] = 0.0

        incentives = []
        for i, j, k, l, m in zip(calc1, calc2, calc3, calc4, calc5):
            sums = [i + j + k + l + m]
            for z in sums:
                incentives.append(min(1500 * self.project_level_inputs['Promised jobs'], z))

        incentives[0] = 0.0

        return incentives
