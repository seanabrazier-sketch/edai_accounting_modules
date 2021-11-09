import statistics
from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = [special_localities_df['Zone Type 1']['Accomack County, VA'],
                                   special_localities_df['Zone Type 2']['Accomack County, VA'],
                                   special_localities_df['Zone Type 3']['Accomack County, VA']]
        self.min_capex = [100000, 500000]
        self.max_benefit = [.20, .20]
        self.eligible_capex = [self.project_level_inputs['Promised capital investment'] - self.min_capex[0],
                               self.project_level_inputs['Promised capital investment'] - self.min_capex[1]]
        self.avg_funding = [statistics.mean([.73, .67]), statistics.mean([.73, .67])]

    def estimated_eligibility(self) -> bool:
        if sum(True for i in self.special_localities if 'Enterprise Zones' in i) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        if self.project_level_inputs['Attraction or Expansion?'] == 'Expansion' and \
                self.project_level_inputs['Promised capital investment'] >= self.min_capex[0]:
            expansion = 'Yes'
        else:
            expansion = 'No'

        if self.project_level_inputs['Attraction or Expansion?'] == 'Relocation' and \
                self.project_level_inputs['Promised capital investment'] >= self.min_capex[1]:
            relocation = 'Yes'
        else:
            relocation = 'No'

        if expansion == 'Yes':
            benefits = [self.eligible_capex[0] * self.max_benefit[0] * self.avg_funding[0]]
        else:
            benefits = [0.0]

        if relocation == 'Yes':
            benefits.append(self.eligible_capex[1] * self.max_benefit[1] * self.avg_funding[1])
        else:
            benefits.append(0.0)

        if self.project_level_inputs['Attraction or Expansion?'] == 'Expansion':
            output = benefits[0]
        else:
            output = benefits[1]

        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives

