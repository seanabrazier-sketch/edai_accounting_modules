from accounting.incentives import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.rd_yearly = kwargs['pnl'].npv_dicts['Research & development']
        self.sales_yearly = kwargs['pnl'].npv_dicts['Sales']
        self.sales_apportionment_rate = kwargs['state_to_manual_share_of_sales']['Idaho']

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        incentives = [0]
        rates = [0.1667, 0.3333, 0.5, 0.6667, 0.8333]
        for i in range(10):
            if i < 5:
                incentives.append(self.rd_yearly[i+1] * 0.03)
            else:
                rd = self.rd_yearly[i+1]
                sales = self.sales_yearly[i+1] * self.sales_apportionment_rate
                rate = min([
                    0.16,
                    rd / sales * rates[i-5]
                ])
                x = sum([self.sales_yearly[i-j-1]*self.sales_apportionment_rate for j in range(4)]) / 4.0
                x2 = x * rate
                x3 = sales - x2
                x4 = rd * 0.5
                x5 = min([x3, x4])
                incentives.append(
                    x5 * 0.05
                )
        return incentives
