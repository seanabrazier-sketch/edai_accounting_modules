
def estimated_taxable_as_share_of_income(income: float):
    if income > 199999:
        return 0.2399
    elif income > 149999:
        return 0.2484
    elif income > 99999:
        return 0.2848
    elif income > 69999:
        return 0.3258
    elif income > 49999:
        return 0.3706
    elif income > 39999:
        return 0.4290
    elif income > 29999:
        return 0.5501
    elif income > 15000:
        return 0.5850
    else:
        return 1.0989
