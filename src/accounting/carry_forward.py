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


INCENTIVE_TYPE_TO_CATEGORY_MAPPING = {
    IncentiveType.NOT_APPLICABLE: IncentiveCategory.NO_CARRYFORWARD,
    IncentiveType.GRANT: IncentiveCategory.PASSTHROUGH,
    IncentiveType.IN_KIND_SERVICES: IncentiveCategory.PASSTHROUGH,
    IncentiveType.CREDIT_CARRYFORWARD: IncentiveCategory.CARRYFORWARD_MATH,
    IncentiveType.CREDIT_REFUNDABLE: IncentiveCategory.CARRYFORWARD_MATH,
    IncentiveType.EXEMPTION: IncentiveCategory.CARRYFORWARD_MATH,
    IncentiveType.CREDIT_NO_CARRYFORWARD: IncentiveCategory.NO_CARRYFORWARD,
}

