from accounting.incentives import *
from accounting.data_store import *

state_specific_sectors_df = pd.read_csv("C:/Users/ferre/Downloads/20210904_State-specific sectors.csv")
state_specific_sectors_df.set_index("Seq. No.", inplace=True)


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oklahoma')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_oos_requirements = 'Yes'
        self.prevailing_wages_state = kwargs['state_to_prevailing_wages']['Oklahoma']
        # Default to state value
        self.bls_wages = kwargs['county_to_prevailing_wages'].get(self.county, self.prevailing_wages_state)

        # state specific sectors
        state_specific_sectors_df['IRS Returns of active corporations'] \
            = state_specific_sectors_df['IRS Returns of active corporations'].str.replace(" +", " ")
        row = state_specific_sectors_df[state_specific_sectors_df['IRS Returns of active corporations']
                                        == self.project_level_inputs['IRS Sector']]
        if not row["QJ qualifying industries"].values:
            self.state_specific = "No"
        else:
            self.state_specific = "Yes"

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['Promised jobs'] >= 10) +
            (self.project_level_inputs['Promised wages'] >= min(103736, (self.bls_wages * 3))) +
            (self.state_specific == 'Yes') +
            (self.min_oos_requirements == 'Yes')) == 4:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = .10 * self.project_level_inputs['Equivalent payroll (BASE)']
        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 10:
                incentives.append(0)
            else:
                incentives.append(output)
        return incentives
