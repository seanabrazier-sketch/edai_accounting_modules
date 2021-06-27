from util.data_loader import load_or_get_from_cache

CONSTRUCTION_WAGES_DF = load_or_get_from_cache('FB_BLS Construction annual pay.csv')
WAGES_DF = load_or_get_from_cache('FB_BLS Annual Pay, total.csv')


class StateWages(object):
    def __init__(self, state: str):
        self.state = state

    def average_wage(self) -> float:
        return WAGES_DF[WAGES_DF.State==self.state]['2019'].mean()

    def average_construction_wage(self) -> float:
        return CONSTRUCTION_WAGES_DF[CONSTRUCTION_WAGES_DF.State==self.state]['2019'].mean()


if __name__ == '__main__':
    for state in ['Alabama', 'Washington', 'Oregon', 'Kansas', 'California', 'Colorado']:
        print('State: {}'.format(state))
        print(StateWages(state).average_wage())
        print(StateWages(state).average_construction_wage())
