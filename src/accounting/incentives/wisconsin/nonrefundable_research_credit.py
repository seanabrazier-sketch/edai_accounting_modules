import pandas as pd
import numpy as np
from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Wisconsin')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.inflation = self.project_level_inputs['Inflation (employment cost index)']
        self.estimated_sales_data = self.project_level_inputs[
            'Estimated sales based on national data (currently used; estimate or manual input)']
        self.nsf_spending = self.pnl_inputs['research_and_development_rate']
        self.QRE_credit = 0.02875

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Project category'] == 'R&D Center':
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        calculations = [0.0, self.estimated_sales_data]
        # first calculation
        for i in range(1, 10):
            result = calculations[-1] * (1 + self.inflation)
            calculations.append(result)
        # Second calculation
        calculations2 = []

        for i in calculations[:4]:
            calculations2.append(self.QRE_credit * i)
        N = 7
        calculations2 = list(np.pad(calculations2, (0, N), 'constant'))
        # Third calculation
        calculations = pd.Series(calculations)
        calculations3 = list(calculations.rolling(3).mean())
        del calculations3[:3]
        del calculations3[-1]
        # Forth calculation
        calculations4 = []
        for i, j in zip(calculations[4:], calculations3):
            calculations4.append(i - (.50 * j))
        # Fifth calculation
        calculations5 = [0.0, 0.0, 0.0, 0.0]
        for i in calculations4:
            calculations5.append(.0575 * i)
        #incentive calculation
        incentives = []
        for i, j in zip(calculations2, calculations5):
            incentives.append(i + j)

        return incentives
