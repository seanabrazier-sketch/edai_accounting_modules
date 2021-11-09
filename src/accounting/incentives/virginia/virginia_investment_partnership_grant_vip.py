from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty, IndustryType


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Virginia')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.legal_presence_3yrs_prior = "No"
        self.local_match_at_least_50percent = "Yes"
        self.real_personal_property = 25000000
        self.capex = kwargs['capex']
        self.capex_amount = (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                               property_type=RealProperty.LAND) +
                             self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                               property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                             self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                               property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                             self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                               property_type=PersonalProperty.FIXTURES))
        self.max_grant = 3000000
        self.discretionary_incentives_group = kwargs['discretionary_incentives_groups'].median('Incentive per job')
        self.median_ipj = \
            self.discretionary_incentives_group['Incentive per job']['Virginia Investment Performance Grant (VIP)']
        self.expected_5_year_amount = self.project_level_inputs['Promised jobs'] * self.median_ipj * 5#years
        self.benefit_to_use = min(self.max_grant, self.expected_5_year_amount)
        self.equal_annual_installment = self.benefit_to_use / 5#years
    def estimated_eligibility(self) -> bool:
        if (self.legal_presence_3yrs_prior == "Yes") \
                + (self.local_match_at_least_50percent == "Yes") \
                + (self.capex_amount >= self.real_personal_property) \
                + ((self.project_level_inputs['High-level category'] == 'Manufacturing') or
                   (self.project_level_inputs['Project category'] == 'R&D center')) == 4:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = self.equal_annual_installment
        incentives = [0.0, output]

        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives
