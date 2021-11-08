from accounting.incentives import *
from util.capex import PersonalProperty
from accounting.data_store import ne_advantage_sectors_df


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Nebraska')

        promised_wages = kwargs['project_level_inputs']['Promised wages']
        promised_jobs = kwargs['project_level_inputs']['Promised jobs']
        promised_capital_investment = kwargs['project_level_inputs']['Promised capital investment']

        prevailing_wages_state = kwargs['state_to_prevailing_wages']['Nebraska']
        # Default to state value
        prevailing_wages_county = kwargs['county_to_prevailing_wages'].get(self.county, prevailing_wages_state)

        # Wages Tier One through Five
        if promised_wages / prevailing_wages_state <= 0.75:
            self.wage_multiple = 0.03
        elif promised_wages / prevailing_wages_state < 1.0:
            self.wage_multiple = 0.04
        elif promised_wages / prevailing_wages_state < 1.25:
            self.wage_multiple = 0.05
        else:
            self.wage_multiple = 0.6

        # Wage Tier Six
        self.new_employee_job_credit = 0.10
        share_of_county_avg_wage = 2.0 * prevailing_wages_county
        share_of_ne_avg_wage = 1.5 * prevailing_wages_state
        self.share_of_avg_wage_to_use = max([share_of_county_avg_wage, share_of_ne_avg_wage])
        print('share_of_avg_wage_to_use: {}'.format(self.share_of_avg_wage_to_use))
        print('ratio: {}'.format(promised_wages / prevailing_wages_state))
        print('age multiple: {}'.format(self.wage_multiple))

        # Tiers
        tiers = ['Type of sector', 'Tier One', 'Tier Two regular',
                 'Tier Two Data center', 'Tier Three', 'Tier Four', 'Tier Five',
                 'Tier Six small', 'Tier Six large', 'Rural Level One',
                 'Rural Level Two']

        high_level_category = kwargs['project_level_inputs']['High-level category']
        eligible_tiers = []
        for tier in tiers:
            if high_level_category in ne_advantage_sectors_df[tier].values.tolist():
                eligible_tiers.append(tier)

        self.eligible_tiers = eligible_tiers
        print('eligible_tiers: {}'.format(eligible_tiers))

    def estimated_eligibility(self) -> bool:
        return len(self.eligible_tiers) > 0

    def estimated_incentives(self) -> List[float]:
        # Todo
        pass
