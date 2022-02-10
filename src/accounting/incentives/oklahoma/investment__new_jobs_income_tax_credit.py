from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


# this one needs both functions finished. Others may just need the first or second
class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oklahoma')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.min_oos_requirements = 'Yes'
        self.min_health_coverage = 'Yes'
        self.capex = kwargs['capex']
        self.pnl = kwargs['pnl']

        self.prevailing_wages_state = kwargs['state_to_prevailing_wages']['Oklahoma']
        # Default to state value
        self.prevailing_wages_county = kwargs['county_to_prevailing_wages'].get(self.county,
                                                                                self.prevailing_wages_state)
        self.bls_wages = min(self.prevailing_wages_state, self.prevailing_wages_county)
        # state specific sectors
        state_specific_sectors_df['IRS Returns of active corporations'] \
            = state_specific_sectors_df['IRS Returns of active corporations'].str.replace(" +", " ")
        row = state_specific_sectors_df[state_specific_sectors_df['IRS Returns of active corporations']
                                        == self.project_level_inputs['IRS Sector']]
        if 'QJ qualifying industries' not in row:
            self.state_specific = "No"
        else:
            self.state_specific = "Yes"

        self.special_localities = float(
            special_localities_df['Population']['Canadian County, OK'])  # needs to be fixed to user county info

    def estimated_eligibility(self) -> bool:
        #### first requirement
        # inellgible
        if ((self.project_level_inputs['Promised jobs'] >= 10) +
            (self.project_level_inputs['Promised wages'] >= (min(103736, 3 * self.bls_wages))) +
            (self.min_oos_requirements == 'Yes') + (self.state_specific == 'Yes')) == 4:
            eligible = 'No'
        else:
            eligible = 'Yes'

        if ((eligible == 'Yes') +
            (self.project_level_inputs['Equivalent payroll (BASE)'] >= 2500000) +
            (self.project_level_inputs['Promised wages'] >= self.bls_wages * 1) +
            (self.state_specific == 'Yes') +
            (self.min_health_coverage == 'Yes') +
            (self.min_oos_requirements == 'Yes')) == 6:
            requirement1 = 'Yes'
        else:
            requirement1 = 'No'

        #### second requirement
        if ((eligible == 'Yes') +
            (self.project_level_inputs['Equivalent payroll (BASE)'] >= 2500000) +
            (self.project_level_inputs['Promised wages'] >= self.bls_wages * 1) +
            (self.state_specific == 'Yes') +
            (self.min_health_coverage == 'Yes') +
            (self.min_oos_requirements == 'Yes')) == 6:
            ineligible = 'Yes'
        else:
            ineligible = 'No'
            # min job requirements
        if self.special_localities >= 3500:
            min_job_req = 5
        else:
            min_job_req = 0
        if self.special_localities >= 7000:
            min_job_req2 = 15
        else:
            min_job_req2 = 0

        if min_job_req == 0 and min_job_req2 == 0:
            min_job_req3 = 10
        else:
            min_job_req3 = 0

        if ((ineligible == 'No') +
            (self.project_level_inputs['Promised jobs'] < 500) +
            (self.project_level_inputs['Promised jobs'] >= max(min_job_req, min_job_req2, min_job_req3)) +
            (self.project_level_inputs['Promised wages'] >= self.bls_wages * 1) +
            (self.state_specific == 'Yes') +
            (self.min_health_coverage == 'Yes')) == 6:
            requirement2 = 'Yes'
        else:
            requirement2 = 'No'

        #### third requirement
        if ((self.project_level_inputs['Promised jobs'] >= 10) +
            (self.project_level_inputs['Promised wages'] >= min(103736, (self.bls_wages * 3))) +
            (self.state_specific == 'Yes') +
            (self.min_oos_requirements == 'Yes')) == 4:
            requirement3 = 'Yes'
        else:
            requirement3 = 'No'

        #### main requirement
        if (requirement1 == 'Yes' or requirement2 == 'Yes' or requirement3 == 'Yes'):
            ineligible2 = 'No'
        else:
            ineligible2 = 'Yes'

        if ineligible2 == 'Yes' and self.project_level_inputs['High-level category'] == 'Manufacturing' and \
                (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                 self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                   property_type=PersonalProperty.FIXTURES)) >= 50000:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        nums1 = [0.0] * 11
        nums1[1] = self.project_level_inputs['Promised jobs'] * 500  # benefit per job

        nums2 = [.01 * (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                          property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                        self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                          property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                        self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                          property_type=PersonalProperty.FIXTURES))]
        for i in range(1, 11):
            nums2.append(self.pnl.npv_dicts['Annual capital expenditures'][i] * .01)

        benefit_per_job = sum(nums1)
        benefit_share_cap_invest = sum(nums2)
        max_10_year = max(benefit_per_job,benefit_share_cap_invest)

        incentives = []
        if max_10_year == benefit_share_cap_invest:
            for i in nums2:
                incentives.append(i)
        else:
            for i in nums1:
                incentives.append(i)

        return incentives
