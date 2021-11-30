from accounting.incentives import *
from accounting.data_store import *
from util.capex import PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Tennessee')
        self.pnl = kwargs['pnl']
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.benefits_df = pd.DataFrame([[0, .01],
                                         [100000000, .03],
                                         [250000000, .05],
                                         [500000000, .07],
                                         [1000000000, .10]],
                                        columns=['Capex band', 'Benefit'])
        self.capex = kwargs['capex']
        self.capex_amount = self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                              property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT)



    def estimated_eligibility(self) -> bool:
        return True

    def estimated_incentives(self) -> List[float]:
        closest = self.benefits_df['Capex band'].sub(self.capex_amount).abs().idxmin()
        idx = self.benefits_df.loc[[closest]]
        benefits = [idx['Benefit'].item()]

        cpxs = []
        for i in range(1, 11):
            cpxs.append(self.pnl.npv_dicts['Annual capital expenditures'][i])

        close_nums = []
        for i in cpxs:
            close_nums.append(self.benefits_df['Capex band'].sub(i).abs().idxmin())

        idxs = []
        for i in close_nums:
            idxs.append(self.benefits_df.loc[[i]])

        for i in idxs:
            benefits.append(i['Benefit'].item())

        incentives = [benefits[0] * self.capex_amount]

        for i, j in zip(benefits[1:], cpxs):
            incentives.append(i * j)

        return incentives
