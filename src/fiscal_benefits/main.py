from fiscal_benefits.state_model import state_model

inputs_basic = {
    'IRS Sector': 'Warehousing and storage',
    'Location Matters crosswalk': 'Distribution center',
    'Promised jobs': 337,
    'Promised capital investment': 76000000,
    'Promised wages': 36511,
    'Attraction or Expansion?': 'Relocation'
}

inputs_adjustable = {
    'P&L Salary state adjuster (on/off)': True,
    'Estimated sales based on national data': 142970881.40,
    'Discount rate': 0.0116,
    'Inflation type': 'Employment cost index',
    'Inflation': 0.028
}

inputs_miscellaneous = {
    'State focus': 'Virginia',
    '10/11 year NPV': 19101513,
    'Capital investment category': 'Industrial',
    'Employment rampup': 1,
    'Construction years': 1,
    'Sector for employment multipliers': 'Nondurable manufacturing',
    'Sector': 'Industrial',
    'Include or exclude inventory': 'Include inventory',
    'Geography': 'City'
}


output_columns = [
    'Category',
    'Sub-category',
    'State, 10-year NPV',
    'Local, 10-year NPV'
]


state_npv_dict, state_values_dict = state_model(
    inputs_basic,
    inputs_adjustable,
    inputs_miscellaneous
)

print(state_npv_dict)
print(state_values_dict)