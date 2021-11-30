from accounting.incentives import *
from accounting.data_store import *
from util.capex import RealProperty, PersonalProperty


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.county = kwargs['county_overrides'].get('Oklahoma')
        self.pnl_inputs = kwargs['pnl_inputs']
        self.project_level_inputs = kwargs['project_level_inputs']
        self.special_localities = float(
            special_localities_df['Population']['Canadian County, OK'])  # fix for user inputs
        self.property_tax = self.pnl_inputs['property_tax_rate']
        self.capex = kwargs['capex']

    def estimated_eligibility(self) -> bool:
        if ((self.project_level_inputs['High-level category'] == 'Distribution center') +
            (self.project_level_inputs['Promised capital investment'] >= 5000000) +
            (self.project_level_inputs['Promised jobs'] >= 100) +
            (self.project_level_inputs['Promised wages'] / 2080 >= 1.75
             * self.project_level_inputs['Federal minimum wage'])) == 4:
            warehouse_requirements = 'Yes'
        else:
            warehouse_requirements = 'No'

        if ((self.project_level_inputs['IRS Sector'] == 'Transportation equipment manufacturing') +
            (self.project_level_inputs['Promised capital investment'] >= 300000000) +
            (self.project_level_inputs['Promised jobs'] >= 1750)) == 3:
            automotive_requirements = 'Yes'
        else:
            automotive_requirements = 'No'
        #####
        if self.special_localities < 75000:
            population_requirements = 250000
        else:
            population_requirements = 1000000
        if ((self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services') +
            (self.project_level_inputs['Promised capital investment'] >= 250000) +
            ("sales_oos" == "sales_oos") +
            (self.project_level_inputs['Equivalent payroll (BASE)'] >= population_requirements)) == 4:
            data_center_requirements1 = 'Yes'
        else:
            data_center_requirements1 = 'No'

        if ((self.project_level_inputs['IRS Sector'] == 'Data processing, hosting, and related services') +
            (self.project_level_inputs['Promised capital investment'] >= 7000000) +
            ("sales_oos" == "sales_oos") +
            (self.project_level_inputs['Equivalent payroll (BASE)'] >= population_requirements)) == 4:
            data_center_requirements2 = 'Yes'
        else:
            data_center_requirements2 = 'No'

        if ((self.project_level_inputs['High-level category'] == 'Manufacturing') +
            (warehouse_requirements == 'Yes') +
            (warehouse_requirements == 'Yes') +
            (automotive_requirements == 'Yes') +
            (data_center_requirements1 == 'Yes') +
            (data_center_requirements2 == 'Yes')) > 0:
            return True
        else:
            return False

    def estimated_incentives(self) -> List[float]:
        output = (self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.CONSTRUCTION_MATERIAL) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=RealProperty.LAND) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.MACHINERY_AND_EQUIPMENT) +
                  self.capex.amount(industry_type=self.pnl_inputs['industry_type'],
                                    property_type=PersonalProperty.FIXTURES)) * self.property_tax

        incentives = [0.0, output]
        for j in range(1, 10):
            if len(incentives[2:]) + 1 >= 5:
                incentives.append(0)
            else:
                incentives.append(output)

        return incentives

