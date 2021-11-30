from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Utah')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.rd_spending = self.pnl_inputs['research_and_development_rate']
        self.fifty_percent = .50
        self.tax_credit_starting = .075
        self.tax_credit_4_years = .05

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        #this one requires three year rolling average so find that - in the file called major_rd_expesnes tax credit
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

        #nums4 = []
        #for i in nums2:
            #nums4.append(i * self.assumed_rate)

        incentives = []
        for i in nums2[:4]:
            incentives.append(i * self.tax_credit_starting)
        for i in nums3[4:]:
            incentives.append(i * self.tax_credit_4_years)

        return incentives
