from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_annual_spend = 5000000
        self.sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.rd_spending = self.pnl_inputs['research_and_development_rate']
        # self.rd_spending = nsf_rd_spending_df['Manual R&D share of sales']['Computer and electronic product manufacturing'] /100
        self.benefit_starting = .05
        self.benefit_expenses = .10
        self.fifty_percent = .50
        self.method = .15
        self.max_per_year = 45000

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        nums1 = [0.0, self.sales_data]
        for i in range(1, 10):
            nums1.append(nums1[-1] * (1 + self.project_level_inputs['Inflation (employment cost index)']))

        nums2 = []
        for i in nums1:
            nums2.append(i * self.rd_spending)

        nums3 = [0.0, 0.0, 0.0, 0.0]

        calculations1 = pd.Series(nums2[1:])
        calculations1 = list(calculations1.rolling(3).mean())
        calculations1 = calculations1[3 - 1:]
        del calculations1[-1]

        for i in calculations1:
            nums3.append(i * self.fifty_percent)
        nums4 = []
        for i, j in zip(nums2, nums3):
            nums4.append(i - j)

        nums5 = []
        for i in nums4[:4]:
            nums5.append(i * self.benefit_starting)
        for i in nums4[4:]:
            nums5.append(i * self.benefit_expenses)

        nums6 = []
        for i in nums2:
            nums6.append(min(self.max_per_year, self.method * i))

        incentives = []
        for i, j in zip(nums5, nums6):
            incentives.append(min(self.max_per_year, max(i, j)))

        return incentives
