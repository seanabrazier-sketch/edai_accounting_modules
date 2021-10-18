from accounting.incentives import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Colorado')
        self.state_unemployment_rate = kwargs['state_to_unemployment_rate']['Colorado']
        self.county_unemployment_rate = \
            kwargs['county_to_unemployment_rate'].get(self.county, self.state_unemployment_rate)
        self.state_per_capita_income = kwargs['state_to_per_capita_income']['Colorado']
        self.county_per_capita_income = \
            kwargs['county_to_per_capita_income'].get(self.county, self.state_per_capita_income)
        self.capex = kwargs['capex']
        self.pnl_inputs = kwargs['pnl_inputs']

        # BENEFITS
        # Investment tax credit
        self.investment_tax_credit_itc = 0.03

        # Job training credit
        self.qualifying_training_expense_pct = 0.12
        self.cost_to_train_employee = kwargs['workforce_programs_ipj_map']['Costs to train employee']
        self.promised_jobs = kwargs['project_level_inputs']['Promised jobs']

        # New Employee Credit, per job
        self.standard_credit_per_job = 1100.0

        # Employer Sponsored Health Insurance, per job
        self.health_insurance_per_job = 1000.0
        self.health_insurance_years = 2

        # R&D tax credit
        self.rd_yearly = kwargs['pnl'].npv_dicts['Research & development']
        self.rd_tax_credit = 0.03

    def estimated_eligibility(self) -> bool:
        if self.county_unemployment_rate > 1.25 * self.state_unemployment_rate \
                or self.county_per_capita_income < 0.75 * self.state_per_capita_income:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]
        for i in range(1, 11):
            to_sum = []
            if i == 1:
                # Investment tax credit
                to_sum.append(self.investment_tax_credit_itc * (
                    self.capex.amount(
                        industry_type=self.pnl_inputs['industry_type'],
                        property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT
                    ) + self.capex.amount(
                        industry_type=self.pnl_inputs['industry_type'],
                        property_type=PersonalProperty.FIXTURES
                    )
                ))
                # Job training credit
                to_sum.append(
                    self.qualifying_training_expense_pct *
                    self.cost_to_train_employee *
                    self.promised_jobs

                )
                # New Employee Credit, per job
                to_sum.append(
                    self.standard_credit_per_job *
                    self.promised_jobs
                )
            if i <= self.health_insurance_years:
                # Employer Sponsored Health Insurance, per job
                to_sum.append(
                    self.health_insurance_per_job *
                    self.promised_jobs
                )
            if i > 2:
                # R&D tax credit
                diff_from_base_year = self.rd_yearly[i] - \
                                      (self.rd_yearly[i-1] + self.rd_yearly[i-2]) / 2.0
                to_sum.append(diff_from_base_year * self.rd_tax_credit)
            incentives.append(sum(to_sum))
        return incentives


