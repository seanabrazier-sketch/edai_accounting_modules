from accounting.incentives import *
from util.capex import PersonalProperty, RealProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Nebraska')

        self.promised_wages = kwargs['project_level_inputs']['Promised wages']
        self.promised_jobs = kwargs['project_level_inputs']['Promised jobs']
        self.promised_capital_investment = kwargs['project_level_inputs']['Promised capital investment']

        self.prevailing_wages_state = kwargs['state_to_prevailing_wages']['Nebraska']
        # Default to state value
        self.prevailing_wages_county = kwargs['county_to_prevailing_wages'].get(self.county, self.prevailing_wages_state)

        # Wages Tier One through Five
        if self.promised_wages / self.prevailing_wages_state <= 0.75:
            self.wage_multiple = 0.03
        elif self.promised_wages / self.prevailing_wages_state < 1.0:
            self.wage_multiple = 0.04
        elif self.promised_wages / self.prevailing_wages_state < 1.25:
            self.wage_multiple = 0.05
        else:
            self.wage_multiple = 0.06

        # Wage Tier Six
        self.new_employee_job_credit = 0.10
        share_of_county_avg_wage = 2.0 * self.prevailing_wages_county
        share_of_ne_avg_wage = 1.5 * self.prevailing_wages_state
        self.share_of_avg_wage_to_use = max([share_of_county_avg_wage, share_of_ne_avg_wage])

        # Tiers
        tiers = ['Tier One', 'Tier Two regular',
                 'Tier Two Data center', 'Tier Three', 'Tier Four', 'Tier Five',
                 'Tier Six small', 'Tier Six large', 'Rural Level One',
                 'Rural Level Two']

        tier_mapping = {
            'Tier One': ['Manufacturing'],
            'Tier Two regular': [
                'Manufacturing',
                'Distribution',
                'Transportation',
                'Storage/warehousing',
                'Telecommunications',
                'Data processing',
                'Financial services',
                'Insurance'
            ],
            'Tier Two Data center': ['Data processing'],
            'Tier Three': [
                'Manufacturing',
                'Distribution',
                'Transportation',
                'Storage/warehousing',
                'Telecommunications',
                'Data processing',
                'Financial services',
                'Insurance'
            ],
            'Tier Four': [
                'Manufacturing',
                'Distribution',
                'Transportation',
                'Storage/warehousing',
                'Telecommunications',
                'Data processing',
                'Financial services',
                'Insurance'
            ],
            'Tier Five': [
                'Manufacturing',
                'Distribution',
                'Transportation',
                'Storage/warehousing',
                'Telecommunications',
                'Data processing',
                'Financial services',
                'Insurance'
            ],
            'Tier Six small': [],
            'Tier Six large': [],
            'Rural Level One': [
                'Manufacturing',
                'Distribution',
                'Transportation',
                'Storage/warehousing',
                'Telecommunications',
                'Data processing',
                'Financial services',
                'Insurance'
            ],
            'Rural Level Two': [
                'Manufacturing',
                'Distribution',
                'Transportation',
                'Storage/warehousing',
                'Telecommunications',
                'Data processing',
                'Financial services',
                'Insurance'
            ]
        }

        high_level_category = kwargs['project_level_inputs']['High-level category']
        rollup_irs_sector = kwargs['project_level_inputs']['Rollup IRS sector']
        project_category = kwargs['project_level_inputs']['Project category']

        eligible_tiers = []
        self.eligibility = []
        for tier in tiers:
            if (tier not in ['Tier Two Data center', 'Tier Six small', 'Tier Six large'] and project_category in ['R&D center', 'Corporate headquarters']) or \
                    high_level_category in tier_mapping[tier]:
                eligible_tiers.append(tier)
                self.eligibility.append(True)
            else:
                self.eligibility.append(False)

        self.eligible_tiers = eligible_tiers
        self.sales_tax_rate = kwargs['pnl_inputs']['state_local_sales_tax_rate']
        self.capex = kwargs['capex']
        self.industry_type = kwargs['pnl_inputs']['industry_type']
        self.property_tax_rate = kwargs['pnl_inputs']['property_tax_rate']

    def estimated_eligibility(self) -> bool:
        return len(self.eligible_tiers) > 0

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]

        for i in range(10):
            investment_credits = [0.0]
            wage = [0.0]
            sales_tax_refund_onetime = [0.0]
            sales_tax_refund_ongoing = [0.0]
            other = [0.0]
            if i < 6 and self.eligibility[0]:
                # 1
                ic_percent = 0.03
                st_ot_percent = 0.5
                investment_credits.append(self.promised_capital_investment * ic_percent)
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 7 and self.eligibility[1]:
                # 2
                ic_percent = 0.1
                st_ot_percent = 1.0
                investment_credits.append(self.promised_capital_investment * ic_percent)
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 7 and self.eligibility[2]:
                # 3
                ic_percent = 0.1
                st_ot_percent = 1.0
                investment_credits.append(self.promised_capital_investment * ic_percent)
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 6 and self.eligibility[3]:
                # 4
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
            if i < 7 and self.eligibility[4]:
                # 5
                ic_percent = 0.1
                st_ot_percent = 1.0
                investment_credits.append(self.promised_capital_investment * ic_percent)
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 7 and self.eligibility[5]:
                # 6
                st_ot_percent = 1.0
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 10 and self.eligibility[6]:
                # 7
                ic_percent = 0.15
                st_ot_percent = 1.0
                investment_credits.append(self.promised_capital_investment * ic_percent)
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 10 and self.eligibility[7]:
                # 8
                ic_percent = 0.15
                st_ot_percent = 1.0
                investment_credits.append(self.promised_capital_investment * ic_percent)
                wage.append(self.promised_wages * self.promised_jobs * self.wage_multiple)
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
                if i < 1:
                    sales_tax_refund_onetime.append(
                        self.sales_tax_rate
                        * self.capex.amount(RealProperty.CONSTRUCTION_MATERIAL, self.industry_type)
                        * st_ot_percent
                    )
            if i < 1 and self.eligibility[8]:
                # 9
                investment_credits.append(self.promised_capital_investment * (2_570.0/50_000.0))
                wage.append(self.promised_jobs * 3_000.0)
                personal_property = self.capex.amount(PersonalProperty.MACHINERY_AND_EQUIPMENT, self.industry_type) \
                    + self.capex.amount(PersonalProperty.FIXTURES, self.industry_type)
                other.append(self.property_tax_rate * personal_property)
            if i < 1 and self.eligibility[9]:
                # 10
                investment_credits.append(self.promised_capital_investment * (2_570.0/50_000.0))
                wage.append(self.promised_jobs * 3_000.0)
            incentives.append(
                max(investment_credits)
                + max(wage)
                + max(sales_tax_refund_onetime)
                + max(sales_tax_refund_ongoing)
                + max(other)
            )
        return incentives
