from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self._health_benefits_required = "Yes"
        self.special_localities = [special_localities_df['Zone Type 1']['Accomack County, VA'],
                                   special_localities_df['Zone Type 2']['Accomack County, VA'],
                                   special_localities_df['Zone Type 3']['Accomack County, VA']]
        self.county_unemployment_rate = kwargs['county_to_unemployment_rate']['Brunswick County, VA']
        self.state_to_unemployment_rate = kwargs['state_to_unemployment_rate']['Virginia']
        self.locality_unemploy_rate = 1.5
        self.hua_threshold = 1.5
        self.wages_table = [12.69, 14.50]
        self.max_jobs = 350

    def estimated_eligibility(self) -> bool:
        if self._health_benefits_required == "Yes" and \
                sum(True for i in self.special_localities if 'Enterprise Zones' in i) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        if self.county_unemployment_rate >= self.state_to_unemployment_rate * self.locality_unemploy_rate \
                and self.project_level_inputs['Promised wages'] / 2080 >= self.hua_threshold * \
                self.project_level_inputs['Federal minimum wage']:
            meets = 'Yes'
        else:  # For now I have them both as yes because I am not sure how to get county data
            meets = 'Yes'

        if meets == 'Yes':
            benefit_high_unemploy = 500
        else:
            benefit_high_unemploy = 0

        if self.project_level_inputs['Promised wages'] / 2080 >= self.wages_table[0]:
            meets_requirements = ['Yes']
            benefit = [500]
        else:
            meets_requirements = ['No']
            benefit = [0]

        if self.project_level_inputs['Promised wages'] / 2080 >= self.wages_table[1]:
            meets_requirements.append('Yes')
            benefit.append(800)
        else:
            meets_requirements.append('No')
            benefit.append(0)

        if all('Yes' == x for x in meets_requirements):
            max_benefit = max(benefit)
        else:
            max_benefit = 0

        if self.county_unemployment_rate >= self.state_to_unemployment_rate * self.locality_unemploy_rate:
            benefit2 = max_benefit + benefit_high_unemploy
        else:
            benefit2 = max(benefit)

        output = benefit2 * min(self.project_level_inputs['Promised jobs'], self.max_jobs)
        incentives = [0.0, output]

        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
