from accounting.incentives import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.wages_assumption = 37950
        self.tax_credit = 3000

    def estimated_eligibility(self) -> bool:
        if self.project_level_inputs['Promised jobs'] < 20 \
                and self.project_level_inputs['Promised wages'] * \
                (1 + (1 - self.project_level_inputs[
                    'Wages as share of total compensation (manuf. vs. services'])) > self.wages_assumption \
                and sum(1 for i in self.project_level_inputs['Project category'] if i == 'R&D Center' and 1 for i in \
                        self.project_level_inputs['Project category'] if i == 'Distribution center' and \
                                                                         1 for i in
                        self.project_level_inputs['High-level category'] if i == 'Manufacturing' and \
                                                                            1 for i in
                        self.project_level_inputs['High-level category'] == 'Information') > 0:

            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0, self.tax_credit * self.project_level_inputs['Promised jobs']]

        for j in range(1, 10):
            if len(incentives) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(self.tax_credit * self.project_level_inputs['Promised jobs'])

        return incentives
