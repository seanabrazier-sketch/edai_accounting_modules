import pandas as pd
import os
from os.path import dirname
from sqlalchemy.engine import Engine


CACHE = {}
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(dirname(dirname(dirname(__file__))), 'data'))
TMP_DATA_DIR = os.environ.get('TMP_DATA_DIR', os.path.join(dirname(dirname(dirname(__file__))), 'sql_data_cache'))


def load_or_get_from_cache(file: str, copy: bool = True, **pandas_kwargs) -> pd.DataFrame:
    if file not in CACHE:
        df = pd.read_csv(os.path.join(DATA_DIR, file), **pandas_kwargs)
        CACHE[file] = df
    df = CACHE[file]
    if copy:
        df = df.copy()
    return df


def load_from_sql_or_get_from_cache(engine: Engine, table: str, copy: bool = True, **pandas_kwargs) -> pd.DataFrame:
    if table not in CACHE:
        file = os.path.join(TMP_DATA_DIR, table + '.json')
        if os.path.isfile(file):
            df = pd.read_json(file)
        else:
            df = pd.read_sql_table(
                table_name=table,
                con=engine,
                **pandas_kwargs
            )
            df.to_json(file)
        CACHE[table] = df
    df = CACHE[table]
    if copy:
        df = df.copy()
    return df