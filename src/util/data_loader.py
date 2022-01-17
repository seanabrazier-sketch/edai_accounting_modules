import pandas
import pandas as pd
import os
from os.path import dirname
from sqlalchemy.engine import Engine


CACHE={}

# DATA_DIR=os.environ.get('DATA_DIR',)
DATA_DIR=os.environ.get('DATA_DIR',os.path.join(dirname(dirname(dirname(__file__))),'data'))

TMP_DATA_DIR=os.environ.get('TMP_DATA_DIR',os.path.join(dirname(dirname(dirname(__file__))),'sql_data_cache'))
path=os.path.join(TMP_DATA_DIR,"20210904_Census ACS 2018_Industry Earni_Heading legend.csv")

def load_or_get_from_cache(file:str,copy:bool=True,**pandas_kwargs)->pd.DataFrame:


    # if the file is not existed in Cache json, then we are going to read it with csv. we pass in the location of the file, as well we are going to pass in the arguments for pandas argument.
    if file not in CACHE:
        df=pd.read_csv(os.path.join(DATA_DIR,file),**pandas_kwargs)
        #after that we are going to append to the cache array to add in the dataframe information
        CACHE[file]=df
    # if the file is already in cache which means that cache[file] exist then CACHE[file] stores information of the dataframe
    # we store new dataframe information by passing back df
    df=CACHE[file]
    # next is the copy function
    if copy:
        df=df.copy()
    return df

def load_cache_csv(file:str):
    path=os.path.join(TMP_DATA_DIR,file+".csv")
    df=pandas.read_csv(path)
    return df

def load_from_sql_or_get_from_cache(engine:Engine,table:str,copy:bool=True,**pandas_kwargs)->pd.DataFrame:

    #if the table list is not in CACHE, we want to create a new direction for file with json extension. After that we can ask if the file already exists in the system, if that is true
    # then we are going to read that file
    # using pandas_json method:
    # if we can't find the file in the system, we are going to pull that from the sql_server
    # so because some machines doesn't have the file config, we can check if the folder already existed if not we are going to create a folder for that
    isExist=os.path.exists(TMP_DATA_DIR)
    if not isExist:
        # so if it not existed we are going to create a file for that
        os.makedirs(TMP_DATA_DIR)
    if table not in CACHE:
        file=os.path.join(TMP_DATA_DIR,table+'.json')
        if os.path.isfile(file):
            df=pd.read_json(file)
        else:
            df=pd.read_sql_table(table_name=table,con=engine,**pandas_kwargs)
            # after that we are going to convert the data into json file
            df.to_json(file)

        #after that we are going to append the information to our cache with the table name. And that table name contains information of the json file.

        CACHE[table]=df
    # the reason that we use df=CACHE[table] is because if there already exist a table in our file we can just look up for cache and returns the table value

    df=CACHE[table]
    if copy:
        df=df.copy()
    return df

