from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Washington')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = [special_localities_df['Zone Type 1']['Adams County, WA'],
                                   special_localities_df['Zone Type 2']['Adams County, WA'],
                                   special_localities_df['Zone Type 3']['Adams County, WA']]

    def estimated_eligibility(self) -> bool:
        if sum(True for i in self.special_localities if 'CEZ' in i) > 0 or \
                sum(True for i in self.special_localities if 'Rural' in i) > 0 \
                and (self.project_level_inputs['High-level category'] == 'Manufacturing' or \
                     self.project_level_inputs['Project category'] == 'R&D Center'):
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        if self.project_level_inputs['Promised wages'] < 40000:
            num = 2000
        else:
            num = 4000
        output = num * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[1:2]) + 1 >= 1:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
