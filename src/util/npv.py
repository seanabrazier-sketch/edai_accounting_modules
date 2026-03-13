try:
    import numpy_financial as npf
    _npf_available = True
except ImportError:
    _npf_available = False

from typing import List

def npv(discount_rate: float, amounts: List[float]):
    if _npf_available:
        return npf.npv(discount_rate, amounts)
    # Pure-Python fallback: NPV = sum( amounts[t] / (1+r)^t ) for t=0..N
    return sum(v / (1 + discount_rate) ** t for t, v in enumerate(amounts))
def excel_npv(discount_rate:float,amounts:List[float]):
    array_add=[]
    for index,i in enumerate(amounts):
            value=i/((1+discount_rate)**(index+1))
            array_add.append(value)
    sum_val=sum(array_add)
    return sum_val


