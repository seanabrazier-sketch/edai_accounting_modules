from enum import Enum


class IncentiveType(Enum):
    NOT_APPLICABLE = 'n/a'
    GRANT = '1. Grant'
    CREDIT_CARRYFORWARD = '4. Credit: Carryforward'
    IN_KIND_SERVICES = '2. In-kind services'
    CREDIT_REFUNDABLE = '5. Credit: Refundable'
    EXEMPTION = '3. Exemption'
    CREDIT_NO_CARRYFORWARD = '6. Credit: No carryforward'

    @staticmethod
    def from_str(string: str):
        if string == IncentiveType.NOT_APPLICABLE.value:
            return IncentiveType.NOT_APPLICABLE
        elif string == IncentiveType.GRANT.value:
            return IncentiveType.GRANT
        elif string == IncentiveType.CREDIT_CARRYFORWARD.value:
            return IncentiveType.CREDIT_CARRYFORWARD
        elif string == IncentiveType.IN_KIND_SERVICES.value:
            return IncentiveType.IN_KIND_SERVICES
        elif string == IncentiveType.CREDIT_REFUNDABLE.value:
            return IncentiveType.CREDIT_REFUNDABLE
        elif string == IncentiveType.EXEMPTION.value:
            return IncentiveType.EXEMPTION
        elif string == IncentiveType.CREDIT_NO_CARRYFORWARD.value:
            return IncentiveType.CREDIT_NO_CARRYFORWARD


class IncentiveCategory(Enum):
    PASSTHROUGH = 'Passthrough'
    CARRYFORWARD_MATH = 'Carryforward math'
    NO_CARRYFORWARD = 'No carryforward'

    @staticmethod
    def from_str(string: str):
        if string == IncentiveCategory.PASSTHROUGH.value:
            return IncentiveCategory.PASSTHROUGH
        elif string == IncentiveCategory.CARRYFORWARD_MATH.value:
            return IncentiveCategory.CARRYFORWARD_MATH
        elif string == IncentiveCategory.NO_CARRYFORWARD.value:
            return IncentiveCategory.NO_CARRYFORWARD


INCENTIVE_TYPE_TO_CATEGORY_MAPPING = {
    IncentiveType.NOT_APPLICABLE: IncentiveCategory.NO_CARRYFORWARD,
    IncentiveType.GRANT: IncentiveCategory.PASSTHROUGH,
    IncentiveType.IN_KIND_SERVICES: IncentiveCategory.PASSTHROUGH,
    IncentiveType.CREDIT_CARRYFORWARD: IncentiveCategory.CARRYFORWARD_MATH,
    IncentiveType.CREDIT_REFUNDABLE: IncentiveCategory.CARRYFORWARD_MATH,
    IncentiveType.EXEMPTION: IncentiveCategory.CARRYFORWARD_MATH,
    IncentiveType.CREDIT_NO_CARRYFORWARD: IncentiveCategory.NO_CARRYFORWARD,
}


RELEVANT_STATE_TAX_LIABILITY_MAP = {
    'State corporate income tax': True,
    'State UI tax': True,
    'State/local sales tax': True,
    'Gross receipts tax': True,
    'Property tax': False,
    'Personal income tax': False,
}


default_personal_income_tax = [0.0, 75_000.0]
for i in range(9):
    default_personal_income_tax.append(default_personal_income_tax[-1] * 0.02)


#def compute_carry_forward_math(npv_dicts, alabama_npv_dicts, sticker_amounts, incentive_category):
def compute_carry_forward_math(npv_dicts, sticker_amounts, incentive_category):
    if 'Personal income tax' not in npv_dicts:
        npv_dicts['Personal income tax'] = default_personal_income_tax

    relevant_tax_liabilities = []
    amounts_to_carryforward = []
    remaining_tax_liabilities = []
    applicable_incentives = []
    adjusted_incentives = []
    for i in range(11):
        #if i == 0:
        npv_dicts_to_use = npv_dicts
        #else:
        #    npv_dicts_to_use = alabama_npv_dicts
        relevant_tax_liability = sum([
            npv_dicts_to_use[k][i] for k, v in RELEVANT_STATE_TAX_LIABILITY_MAP.items()
            if v
        ])
        relevant_tax_liabilities.append(relevant_tax_liability)
        if i < 2:
            applicable_incentive_amount = sticker_amounts[i]
        else:
            applicable_incentive_amount = sticker_amounts[i] + amounts_to_carryforward[i-1]
        adjusted_incentive_to_take = (
            applicable_incentive_amount
            if incentive_category == IncentiveCategory.PASSTHROUGH
            else min([relevant_tax_liability, applicable_incentive_amount])
        )
        amount_to_carryforward = 0
        if i > 0:
            amount_to_carryforward = (
                0 if incentive_category == IncentiveCategory.NO_CARRYFORWARD
                else max([0, applicable_incentive_amount - adjusted_incentive_to_take])
            )
        remaining_tax_liability = (
            relevant_tax_liability
            if incentive_category == IncentiveCategory.PASSTHROUGH
            else relevant_tax_liability - adjusted_incentive_to_take
        )
        applicable_incentives.append(applicable_incentive_amount)
        adjusted_incentives.append(adjusted_incentive_to_take)
        amounts_to_carryforward.append(amount_to_carryforward)
        remaining_tax_liabilities.append(remaining_tax_liability)

    print(f'relevant_tax_liabilities: {relevant_tax_liabilities}')
    print(f'applicable_incentives: {applicable_incentives}')
    print(f'adjusted_incentives: {adjusted_incentives}')
    print(f'amounts_to_carryforward: {amounts_to_carryforward}')
    print(f'remaining_tax_liabilities: {remaining_tax_liabilities}')
    return remaining_tax_liabilities