import numpy_financial as npf
from typing import List
def npv(discount_rate:float,amounts:List[float]):
    return npf.npv(discount_rate,amounts)
def excel_npv(discount_rate:float,amounts:List[float]):
    array_add=[]
    for index,i in enumerate(amounts):
            value=i/((1+discount_rate)**(index+1))
            array_add.append(value)
    sum_val=sum(array_add)
    return sum_val


