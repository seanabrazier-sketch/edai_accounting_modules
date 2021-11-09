from accounting.incentives import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.prevailing_wages = kwargs['state_to_prevailing_wages']['Colorado']
        self.promised_wages = kwargs['project_level_inputs']['Promised wages']
        self.promised_jobs = kwargs['project_level_inputs']['Promised jobs']
        self.capex = kwargs['capex']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.pnl = kwargs['pnl']
        self.project_category = kwargs['project_level_inputs']['Project category']
        self.state_local_sales_tax_rate = kwargs['pnl_inputs']['state_local_sales_tax_rate']
        self.rd_yearly = kwargs['pnl'].npv_dicts['Research & development']

    def estimated_eligibility(self) -> bool:
        if self.promised_wages >= self.prevailing_wages * 1.20:
            # check benefits rollup
            return self.promised_jobs > 0
        return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]

        is_distribution_center = self.project_category == 'Distribution center'

        qualified_investment = (self.capex.amount(
            industry_type=self.pnl_inputs['industry_type'],
            property_type=RealProperty.LAND
        ) + self.capex.amount(
            industry_type=self.pnl_inputs['industry_type'],
            property_type=RealProperty.CONSTRUCTION_MATERIAL
        ) + self.capex.amount(
            industry_type=self.pnl_inputs['industry_type'],
            property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT
        ))

        num_years = 5
        if qualified_investment >= 10_000_000:
            rate_to_use = 0.10
        else:
            rate_to_use = 0.05

        for i in range(10):
            if i < num_years:
                qualifying_this_year = (qualified_investment * rate_to_use) / num_years
            else:
                qualifying_this_year = 0.0
            sales_tax_exemptions = self.pnl.npv_dicts['State/local sales tax'][i+1]
            if is_distribution_center:
                sales_tax_exemptions += (
                        self.state_local_sales_tax_rate *
                        self.pnl.npv_dicts['Annual capital expenditures'][i + 1]
                )

            research_credit = 0.0
            if qualified_investment >= 500_000:
                # research tax
                if i < 3:
                    research_credit = self.rd_yearly[i + 1] * 0.0455
                else:
                    avg_3_years = sum(self.rd_yearly[i - 2:i + 1]) / 3
                    avg_3_years_reduced = avg_3_years * 0.50
                    research_credit = (self.rd_yearly[i + 1] - avg_3_years_reduced) * 0.0455

            incentives.append(
                qualifying_this_year +
                sales_tax_exemptions +
                research_credit
            )
        return incentives