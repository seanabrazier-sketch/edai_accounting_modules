from util.data_loader import load_or_get_from_cache

STATE_TAX_DF = load_or_get_from_cache('PersonalIncomeTax.csv').fillna(0.0)
STATE_TAX_DF['Rates'] = STATE_TAX_DF['Rates'].apply(lambda x: float(x.split(' ')[0].replace('%', ''))/100)


def convert_dollars_to_float(x):
    return float(x.replace('$', '').replace(',', '')) if isinstance(x, str) else x


for col in ['Brackets', 'Deduction', 'Exemption']:
    STATE_TAX_DF[col] = STATE_TAX_DF[col].apply(convert_dollars_to_float)


class PersonalIncomeTax(object):
    def __init__(self, salary: float, state: str):
        self.salary = salary
        self.state = state
        df = STATE_TAX_DF[STATE_TAX_DF.State==self.state]
        deduction = df['Deduction'].sum()
        exemption = df['Exemption'].sum()
        taxable_income = salary - deduction - exemption
        brackets = df[df.Brackets < taxable_income]
        if len(brackets) == 1:
            liability = brackets['Rates'].values.tolist()[0] * taxable_income
        elif len(brackets) == 0:
            liability = 0.0
        else:
            liability = 0.0
            taxable_income_remaining = taxable_income
            last_row = None
            for i in range(len(brackets)-1):
                row = df.iloc[i]
                next_row = df.iloc[i+1]
                last_row = next_row
                diff = next_row['Brackets'] - row['Brackets']
                if diff < taxable_income_remaining:
                    liability += row['Rates'] * diff
                    taxable_income_remaining -= diff
                else:
                    liability += taxable_income_remaining * row['Rates']
                    taxable_income_remaining = 0
            liability += last_row['Rates'] * taxable_income_remaining

        self._tax_rate = liability / taxable_income
        self._effective_tax_rate = liability / salary

    def tax_rate(self) -> float:
        return self._tax_rate

    def effective_tax_rate(self) -> float:
        return self._effective_tax_rate


if __name__ == '__main__':
    for state in ['Alabama', 'Washington', 'Oregon', 'Kansas', 'California', 'Colorado']:
        print('State: {}'.format(state))
        print(PersonalIncomeTax(60000, state).tax_rate())
        print(PersonalIncomeTax(60000, state).effective_tax_rate())
        print(PersonalIncomeTax(120000, state).tax_rate())
        print(PersonalIncomeTax(120000, state).effective_tax_rate())
        print(PersonalIncomeTax(1200000, state).tax_rate())
        print(PersonalIncomeTax(1200000, state).effective_tax_rate())
