from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oregon')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = special_localities_df['Zone Type 3']['Benton County, OR']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.property_tax = self.pnl_inputs['property_tax_rate']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        threshold_df = []
        if self.special_localities == 'Rural' and self.project_level_inputs['Promised capital investment'] < 500000000:
            threshold_df.append('Yes')
        else:
            threshold_df.append('No')

        if self.special_localities == 'Rural' and self.project_level_inputs['Promised capital investment'] >= 500000000:
            threshold_df.append('Yes')
        else:
            threshold_df.append('No')

        if self.special_localities == 'Rural' and self.project_level_inputs[
            'Promised capital investment'] >= 1000000000:
            threshold_df.append('Yes')
        else:
            threshold_df.append('No')
        # because it is urban it will give a yes so this needs to be fixed eventually for user input county
        if self.special_localities == 'rban':  # changes spelling just to give it a no, later with fix
            threshold_df.append('Yes')
        else:
            threshold_df.append('No')

        add_data = pd.DataFrame([[threshold_df[0], "Rural Capex < 500M", 25000000],
                                 [threshold_df[1], "Rural Capex 500M-1B", 50000000],
                                 [threshold_df[2], "Rural 1B", 100000000],
                                 [threshold_df[3], "Rural Capex <500M", 100000000]])
        add_data.columns = ['Meets', 'Capex', 'Value']

        boolean_findings = add_data['Meets'].str.contains('Yes')
        boolean_findings = str(boolean_findings)

        if 'True' in boolean_findings:
            match = add_data[add_data['Meets'].str.contains('Yes')]
            value = match['Value'].item()
        else:
            value = 100000000

        if self.project_level_inputs['Promised capital investment'] >= value:
            return True, value
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        x, value = self.estimated_eligibility()
        calc = max(((self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                       property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                     self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                       property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                     self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                       property_type=PersonalProperty.FIXTURES)) - value), 0.0)

        nums1 = [calc * self.property_tax] * 11
        nums1[0] = 0.0

        nums2 = []
        for i in nums1:
            nums2.append(i - (min(2500000, .25 * i)))

        incentives = []
        for i, j in zip(nums1, nums2):
            incentives.append(i - j)

        return incentives
