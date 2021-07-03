from util.data_loader import load_or_get_from_cache
from enum import Enum

PROPERTY_TAX_DF = load_or_get_from_cache('PropertyTax.csv')


def convert_percentages_to_float(x):
    return float(x.replace('%', '').replace(',', ''))/100 if isinstance(x, str) else x


for col in ['Tax Rate 100k', 'Tax Rate 1M', 'Tax Rate 25M']:
    PROPERTY_TAX_DF[col] = PROPERTY_TAX_DF[col].apply(convert_percentages_to_float)


class PropertyType(Enum):
    Industrial = "Industrial"
    Commercial = "Commercial"


class RuralOrCity(Enum):
    Rural = "Rural"
    City = "City"


class PropertyTax(object):
    def __init__(self, state: str):
        self.state = state
        self.df = PROPERTY_TAX_DF[PROPERTY_TAX_DF.State==self.state]

    def tax_rate(self, property_type: PropertyType, rural_or_city: RuralOrCity = None) -> float:
        if rural_or_city is None:
            return self.df[self.df.Type==property_type.value]['Tax Rate 1M'].mean()
        else:
            return self.df[(self.df.Type == property_type.value)&(self.df.RuralOrCity == rural_or_city.value)]['Tax Rate 1M'].mean()


if __name__ == '__main__':
    for state in ['Alabama', 'Washington', 'Oregon', 'Kansas', 'California', 'Colorado']:
        print('State: {}'.format(state))
        print(PropertyTax(state).tax_rate(PropertyType.Commercial))
        print(PropertyTax(state).tax_rate(PropertyType.Industrial))
        print(PropertyTax(state).tax_rate(PropertyType.Commercial, RuralOrCity.City))
        print(PropertyTax(state).tax_rate(PropertyType.Industrial, RuralOrCity.City))
        print(PropertyTax(state).tax_rate(PropertyType.Commercial, RuralOrCity.Rural))
        print(PropertyTax(state).tax_rate(PropertyType.Industrial, RuralOrCity.Rural))
