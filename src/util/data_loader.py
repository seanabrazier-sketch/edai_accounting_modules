import pandas as pd
import os
from os.path import dirname

CACHE = {}
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(dirname(dirname(dirname(__file__))), 'data'))


def load_or_get_from_cache(file: str, copy: bool = True, **pandas_kwargs) -> pd.DataFrame:
    if file not in CACHE:
        df = pd.read_csv(os.path.join(DATA_DIR, file), **pandas_kwargs)
        CACHE[file] = df
    df = CACHE[file]
    if copy:
        df = df.copy()
    return df
