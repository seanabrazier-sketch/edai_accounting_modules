from enum import Enum
from typing import Union


class RealProperty(Enum):
    LAND = 'Land'
    CONSTRUCTION_MATERIAL = 'Construction material'
    CONSTRUCTION_LABOR = 'Construction labor'


class PersonalProperty(Enum):
    MACHINERY_AND_EQUIPMENT = 'Machinery and equipment'
    FIXTURES = 'Fixtures'
    INVENTORY = 'Inventory'


class IndustryType(Enum):
    INDUSTRIAL = 'Industrial'
    DISTRIBUTION_CENTER = 'Distribution center'
    DATA_CENTER = 'Data center'
    COMMERCIAL = 'Commercial'

    @staticmethod
    def from_str(_str: str):
        if _str == 'Industrial':
            return IndustryType.INDUSTRIAL
        elif _str == 'Distribution center':
            return IndustryType.DISTRIBUTION_CENTER
        elif _str == 'Data center':
            return IndustryType.DATA_CENTER
        elif _str == 'Commercial':
            return IndustryType.COMMERCIAL
        else:
            raise RuntimeError('No Industry Type called: {}'.format(_str))


SHARES_INDUSTRIAL = SHARES_DISTRIBUTION_CENTER = SHARES_DATA_CENTER = {
    RealProperty.LAND: 0.125,
    RealProperty.CONSTRUCTION_MATERIAL: 0.2,
    RealProperty.CONSTRUCTION_LABOR: 0.3,
    PersonalProperty.MACHINERY_AND_EQUIPMENT: 0.3125,
    PersonalProperty.FIXTURES: 0.0625,
    PersonalProperty.INVENTORY: 0.0
}

SHARES_COMMERCIAL = {
    RealProperty.LAND: 0.1,
    RealProperty.CONSTRUCTION_MATERIAL: 0.293333333333333,
    RealProperty.CONSTRUCTION_LABOR: 0.44,
    PersonalProperty.MACHINERY_AND_EQUIPMENT: 0.0,
    PersonalProperty.FIXTURES: 0.166666666666667,
    PersonalProperty.INVENTORY: 0.0
}

SHARES_MAP = {
    IndustryType.INDUSTRIAL: SHARES_INDUSTRIAL,
    IndustryType.DATA_CENTER: SHARES_DATA_CENTER,
    IndustryType.DISTRIBUTION_CENTER: SHARES_DISTRIBUTION_CENTER,
    IndustryType.COMMERCIAL: SHARES_COMMERCIAL
}


class CapexReport(object):
    def __init__(self, capex: float):
        self.capex = capex

    def amount(self,
               property_type: Union[PersonalProperty, RealProperty],
               industry_type: IndustryType
               ) -> float:
        return self.capex * SHARES_MAP[industry_type][property_type]

    def total_taxable_real_property(self, industry_type: IndustryType) -> float:
        return sum([self.amount(property_type, industry_type)
                    for property_type in RealProperty])

    def total_taxable_personal_property(self, industry_type: IndustryType) -> float:
        return sum([self.amount(property_type, industry_type)
                    for property_type in PersonalProperty])

    def total_taxable_real_and_personal_property(self, industry_type: IndustryType) -> float:
        return self.total_taxable_personal_property(industry_type) \
               + self.total_taxable_real_property(industry_type)


def capex_report(
        capex: float
) -> CapexReport:
    return CapexReport(capex=capex)


# Test
if __name__ == '__main__':
    my_report = capex_report(capex=80000000)
    for industry_type in IndustryType:
        print(f'Industry {industry_type.value} -> total_taxable_real_property: {my_report.total_taxable_real_property(industry_type)}')
        print(f'Industry {industry_type.value} -> total_taxable_personal_property: {my_report.total_taxable_personal_property(industry_type)}')
        print(f'Industry {industry_type.value} -> total_taxable_real_and_personal_property: {my_report.total_taxable_real_and_personal_property(industry_type)}')
        print('----------------------')

