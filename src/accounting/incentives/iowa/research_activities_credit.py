from accounting.incentives import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.rd_yearly = kwargs['pnl'].npv_dicts['Research & development']

    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        incentives = [0]
        for i in range(10):
            if i < 3:
                incentives.append(self.rd_yearly[i+1] * 0.0455)
            else:
                avg_3_years = sum(self.rd_yearly[i-2:i+1]) / 3
                avg_3_years_reduced = avg_3_years * 0.50
                incentives.append(
                    (self.rd_yearly[i+1] - avg_3_years_reduced) * 0.0455
                )
        return incentives
