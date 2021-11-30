import pandas as pd

from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Texas')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.include_EZ = 'No'  # fix this later, it was a hardcoded no and referenced special local instead of something else
        self.state_local_sales_tax = self.pnl_inputs['state_local_sales_tax_rate']
        self.sales_tax_exemption = 'Yes'
        self.capex = kwargs['capex']
        self.benefits_df = pd.DataFrame([[40000, 'Half enterprise project 1', 10, 2500 * 10, 2500],
                                         [400000, 'Half enterprise project 2', 25, 2500 * 25, 2500],
                                         [1000000, 'Half enterprise project 3', 125, 2500 * 125, 2500],
                                         [5000000, 'Half enterprise project 4', 250, 2500 * 250, 2500],
                                         [5000000, 'Enterprise project', 500, 2500 * 500, 2500],
                                         [149999999, 'Double jumbo project', 500, 5000 * 500, 5000],
                                         [250000000, 'Triple jumbo project', 500, 7500 * 500, 7500]],
                                        columns=['Capital investment below', 'Refund per job allocated',
                                                 'Max # of jobs allocated',
                                                 'Max potential refund', 'Max refund per job'])
        self.promised_jobs = self.project_level_inputs['Promised jobs']
        self.closest = self.benefits_df['Capital investment below'].sub(self.promised_jobs).abs().idxmax()
        self.idx = self.benefits_df.loc[[self.closest]]
        self.refund_per_job = self.idx.loc[self.closest, 'Refund per job allocated']

    def estimated_eligibility(self) -> bool:
        return False

    def estimated_incentives(self) -> List[float]:
        if self.sales_tax_exemption == 'Yes':
            calc = self.state_local_sales_tax * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                   property_type=RealProperty.CONSTRUCTION_MATERIAL)
                                                 +
                                                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                   property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)
                                                 +
                                                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                                                   property_type=PersonalProperty.FIXTURES))

        output = [calc]
        for j in range(0, 10):
            if len(output) + 1 >= 1:
                output.append(0)
            else:
                output.append(calc)

        row1 = self.benefits_df[self.benefits_df['Refund per job allocated'].str.contains(self.refund_per_job)]
        row2 = self.benefits_df[self.benefits_df['Refund per job allocated'].str.contains(self.refund_per_job)]

        benefit1 = row1.loc[6, 'Max # of jobs allocated']
        benefit2 = row2.loc[6, 'Max refund per job']

        incentives = []
        for i in output:
            incentives.append(min(i, (benefit2 *
                                      min(benefit1, self.project_level_inputs['Promised jobs']))))

        return incentives
