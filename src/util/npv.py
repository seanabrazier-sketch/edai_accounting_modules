import numpy_financial as npf
from typing import List


def npv(discount_rate: float, amounts: List[float]):
    return npf.npv(discount_rate, amounts)