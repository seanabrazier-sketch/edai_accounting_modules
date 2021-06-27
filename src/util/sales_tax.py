from util.data_loader import load_or_get_from_cache

SALES_TAX_DF = load_or_get_from_cache('FB_Tax Foundation Sales Tax.csv')
SALES_TAX_DF.set_index(['State to use'], drop=True, inplace=True)


class SalesTax(object):
    @staticmethod
    def combined_rate(state: str) -> float:
        if state not in SALES_TAX_DF.index:
            raise RuntimeError('State {} is not found in the SALES_TAX_DF!'.format(state))
        return float(SALES_TAX_DF.loc[state]['Combined S&L Rate'].replace('%', ''))/100


if __name__=='__main__':
    print(SALES_TAX_DF.head(5))
    print(SalesTax.combined_rate('Oregon'))
    print(SalesTax.combined_rate('California'))