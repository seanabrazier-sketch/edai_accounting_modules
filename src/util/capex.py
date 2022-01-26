#import
from enum import Enum
from typing import Union
# first we are going to create an industry type class enum
# this will return us with the value of the String of each eleement
# for this capex module, it is mainly the total taxable that matters
# first we have to calculate the total taxable real property of industrial






class IndustryType(Enum):
    INDUSTRIAL='Industrial'
    DISTRIBUTION_CENTER='Distribution Center'
    DATA_CENTER='Data Center'
    COMMERCIAL='Commercial'

class PersonalProperty(Enum):
    MACHINERY_AND_EQUIPMENT='Machine and equipment'
    FIXTURES='Fixtures'
    INVENTORY='Inventory'
# similarly we are going to crate a personal Property Enum
# which contains element of machienary and equipment

class RealProperty(Enum):
    LAND='Land'
    CONSTRUCTION_MATERIAL='Construction Material'
    CONSTRUCTION_LABOR='Construction Labor'
# the next is we are going to crate Real property enum type which contains string of that

    @staticmethod
    def from_str(_str:str):
        if _str=="Industrial":
            return IndustryType.INDUSTRIAL
        elif _str=="Distribution center":
            return IndustryType.DISTRIBUTION_CENTER
        elif _str=="Data center":
            return IndustryType.DATA_CENTER
        elif _str=="Commercial":
            return IndustryType.COMMERCIAL
        else:
            raise RuntimeError('No Industry Type Called: {}'.format(_str))

# this class contain a static method which can be called




SHARES_INDUSTRIAL=SHARES_DISTRIBUTION_CENTER=SHARES_DATA_CENTER={
    RealProperty.LAND:0.125,
    RealProperty.CONSTRUCTION_MATERIAL: 0.2,
    RealProperty.CONSTRUCTION_LABOR: 0.3,
    PersonalProperty.MACHINERY_AND_EQUIPMENT: 0.3125,
    PersonalProperty.FIXTURES: 0.0625,
    PersonalProperty.INVENTORY: 0.0
}

# we are going to create a json array with share indistrial shares distributioncenter and shares data center
# this json variable contains information on realpropety .alnd


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
# data=Union[PersonalProperty, RealProperty]
# print(SHARES_MAP[IndustryType.DATA_CENTER][RealProperty.CONSTRUCTION_MATERIAL])


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
        return self.total_taxable_personal_property(industry_type)+ self.total_taxable_real_property(industry_type)

def capex_report(capex: float) -> CapexReport:
    return CapexReport(capex=capex)

#the function total_taxable_real_property takes in argument of IndustryType
# it returns the union of Personal Property and Real Property
# now if you pass in the industry _type
# it will calculate the industry type by returning capex*Shares_Map[indsutrytype] which in insertedand property type
# now we move our function to total_taxable_real_rpoeprty
# this function called in the sum of industry_type which is industrial distribution and etc
# the only different is taht it will calculate the sum of each columns
# summary:
# this class return the total_taxtable_real_and_personal_property





if __name__ == '__main__':
    my_report = capex_report(capex=80000000)
    for industry_type in IndustryType:
        print(
            f'Industry {industry_type.value} -> total_taxable_real_property: {my_report.total_taxable_real_property(industry_type)}')
        print(
            f'Industry {industry_type.value} -> total_taxable_personal_property: {my_report.total_taxable_personal_property(industry_type)}')
        print(
            f'Industry {industry_type.value} -> total_taxable_real_and_personal_property: {my_report.total_taxable_real_and_personal_property(industry_type)}')
        print('----------------------')

