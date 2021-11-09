import importlib
import re


def get_incentive_program(state, program, **kwargs):
    program_clean = re.sub("[^0-9a-zA-Z ]+", "", program).replace(' ', '_').lower()
    cls = getattr(importlib.import_module(f'accounting.incentives.{state.lower().replace(" ", "_")}.{program_clean}'), 'IncentiveProgram')
    return cls(**kwargs)
