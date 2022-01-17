import re

# for state, programs in incentive_programs_by_state.items():
#     print('State: {}'.format(state))
def name(program):
    program_clean = re.sub("[^0-9a-zA-Z ]+", "", program).replace(' ', '_').lower()
    return program_clean
print(name("Skills Enhancement Fund (SEF)"))

import urllib.request
import pandas as pd
import os, shutil
from zipfile import ZipFile

# url = 'https://www.va.gov/vetdata/docs/Demographics/New_Vetpop_Model/9L_VetPop2018_County.xlsx'
# fname = 'va_veteran_pop.xlsx'
# fname_out = 'va_veteran_pop.csv'
#
# if not os.path.isfile(fname):
#     urllib.request.urlretrieve(url,fname)
#
# df = pd.read_excel(fname, skiprows=6)
# df.rename(columns={i: 'pop_'+str(i.year) for i in df.columns[2:]}, inplace=True)
# df.rename(columns={df.columns[1]: 'county'}, inplace=True)
# df.to_csv(fname_out)