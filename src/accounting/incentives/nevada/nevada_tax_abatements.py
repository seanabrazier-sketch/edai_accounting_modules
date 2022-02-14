from accounting.incentives import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_type = kwargs['project_level_inputs']['Project type']
        self.promised_capital_investment = kwargs['project_level_inputs']['Promised capital investment']
        self.promised_jobs = kwargs['project_level_inputs']['Promised jobs']
        self.promised_wages = kwargs['project_level_inputs']['Promised wages']
        self.prevailing_wages = kwargs['state_to_prevailing_wages']['Nevada']

        # assume Urban
        self.geography = 'Urban'
        self.is_manufacturing = kwargs['project_level_inputs']['High-level category'] == 'Manufacturing'
        self.is_data_center = kwargs['project_level_inputs']['IRS Sector'] == 'Data processing, hosting, and related services'
        self.is_aviation_manufacturing = kwargs['project_level_inputs']['IRS Sector'] == 'Transportation equipment manufacturing'
        self.sales_tax_rate = kwargs['pnl_inputs']['state_local_sales_tax_rate']
        self.target_sales_tax_rate = 0.02 if self.project_type == 'New' else 0.046

        self.capital_investment_reqs = []
        self.jobs_reqs = []
        self.minimum_wages_reqs = [1.0 for _ in range(6)]

        if self.geography == 'Urban':
            if self.project_type == 'New':
                self.jobs_reqs.extend([50, 50, 50, 50, 5, 10])
                if self.is_manufacturing:
                    self.capital_investment_reqs.extend(
                        [1_000_000, 1_000_000, 5_000_000, 5_000_000, 250_000, 25_000_000]
                    )
                else:
                    self.capital_investment_reqs.extend(
                        [1_000_000, 1_000_000, 1_000_000, 1_000_000, 250_000, 25_000_000]
                    )
            else:
                self.jobs_reqs.extend([25, 25, 25, 25, 3, 10])
                if self.is_manufacturing:
                    self.capital_investment_reqs.extend(
                        [0, 0, 0, 0, 250_000, 25_000_000]
                    )
                else:
                    self.capital_investment_reqs.extend(
                        [0, 0, 0, 0, 250_000, 25_000_000]
                    )
        else:
            if self.project_type == 'New':
                self.jobs_reqs.extend([10, 10, 10, 10, 5, 10])
                if self.is_manufacturing:
                    self.capital_investment_reqs.extend(
                        [250_000, 250_000, 1_000_000, 1_000_000, 250_000, 25_000_000]
                    )
                else:
                    self.capital_investment_reqs.extend(
                        [250_000, 250_000, 250_000, 250_000, 250_000, 25_000_000]
                    )
            else:
                self.jobs_reqs.extend([6, 6, 6, 6, 3, 10])
                if self.is_manufacturing:
                    self.capital_investment_reqs.extend(
                        [0, 0, 0, 0, 250_000, 25_000_000]
                    )
                else:
                    self.capital_investment_reqs.extend(
                        [0, 0, 0, 0, 250_000, 25_000_000]
                    )

        self.eligibles = []
        for i in range(6):
            if i == 4 and not self.is_aviation_manufacturing:
                self.eligibles.append(False)
            elif i == 5 and not self.is_data_center:
                self.eligibles.append(False)
            elif self.promised_capital_investment >= self.capital_investment_reqs[i] and \
                    self.promised_jobs >= self.jobs_reqs[i] and \
                    self.promised_wages >= self.minimum_wages_reqs[i]:
                self.eligibles.append(True)
            else:
                self.eligibles.append(False)

        capex = kwargs['capex']
        industry_type = kwargs['pnl_inputs']['industry_type']
        construction_material = capex.amount(RealProperty.CONSTRUCTION_MATERIAL, industry_type)
        total_personal_property = (
                capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, industry_type)
                + capex.amount(PersonalProperty.FIXTURES, industry_type)
        )

        self.total_real_and_personal_property = (
                total_personal_property + construction_material
        )
        self.property_tax_rate = kwargs['pnl_inputs']['property_tax_rate']
        self.annual_capital_expenditures = kwargs['pnl'].npv_dicts['Annual capital expenditures']

    def estimated_eligibility(self) -> bool:
        return any(self.eligibles)

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]

        sales_tax_diff = self.sales_tax_rate - self.target_sales_tax_rate

        if self.eligibles[0]:
            incentives[0] += self.total_real_and_personal_property * sales_tax_diff
        if self.eligibles[4]:
            incentives[0] += self.total_real_and_personal_property * sales_tax_diff
        if self.eligibles[5]:
            incentives[0] += self.total_real_and_personal_property * sales_tax_diff

        for i in range(10):
            incentive = 0.0
            if i < 4:
                # Modified business tax abatement
                if self.eligibles[1]:
                    if self.promised_wages > 50_000:
                        incentive += 0.5 * 0.01475 * self.promised_jobs * self.promised_wages

            if self.eligibles[0]:
                incentive += self.total_real_and_personal_property * sales_tax_diff
            if self.eligibles[2]:
                incentive += self.property_tax_rate * 0.5 * self.total_real_and_personal_property
            if self.eligibles[4]:
                incentive += self.annual_capital_expenditures[i+1] * sales_tax_diff + 0.5 * self.property_tax_rate * self.total_real_and_personal_property
            if self.eligibles[5]:
                incentive += self.annual_capital_expenditures[i+1] * sales_tax_diff + 0.75 * self.property_tax_rate * self.total_real_and_personal_property

            incentives.append(incentive)

        return incentives