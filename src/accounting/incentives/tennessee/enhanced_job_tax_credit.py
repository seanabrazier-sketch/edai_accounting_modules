from accounting.incentives import *
from accounting.data_store import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Tennessee')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        # fix this to county level eventually
        self.special_localities = special_localities_df['Zone Type 2']['Knox County, TN']
        self.min_capex = 500000
        self.meets_requirements = []

    def estimated_eligibility(self) -> bool:
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

        if geo_tier == 'Tier 2' and self.project_level_inputs['Promised jobs'] >= 25 \
                and self.project_level_inputs['Promised capital investment'] >= self.min_capex:
            self.meets_requirements.append('Yes')
        else:
            self.meets_requirements.append('No')

        if geo_tier == 'Tier 3' and self.project_level_inputs['Promised jobs'] >= 20 \
                and self.project_level_inputs['Promised capital investment'] >= self.min_capex:
            self.meets_requirements.append('Yes')
        else:
            self.meets_requirements.append('No')

        if geo_tier == 'Tier 4' and self.project_level_inputs['Promised jobs'] >= 10 \
                and self.project_level_inputs['Promised capital investment'] >= self.min_capex:
            self.meets_requirements.append('Yes')
        else:
            self.meets_requirements.append('No')

        if (('Tier 2' == geo_tier and self.meets_requirements[0] == 'Yes')
            + ('Tier 3' == geo_tier and self.meets_requirements[1] == 'Yes')
            + ('Tier 4' == geo_tier and self.meets_requirements[2] == 'Yes')) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        global year, years
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
        ##############################
        if geo_tier == 'Tier 1':
            years = 0  # same as n/a
        if geo_tier == 'Tier 2':
            years = 3
        if geo_tier == 'Tier 3':
            years = 5
        if geo_tier == 'Tier 4':
            years = 5

        output = 4500 * self.project_level_inputs['Promised jobs']
        incentives = [0.0, output]
        for i in range(1, 10):
            if years == 0:
                incentives.append(output)

            elif len(incentives[2:]) + 1 >= years:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
