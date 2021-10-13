from accounting.data_store import irs_is_statements_df

irs_is_statements_df.columns = [c.strip().replace('  ', ' ').lower() for c in irs_is_statements_df.columns.tolist()]

industry_cols = irs_is_statements_df.columns.tolist()
industry_cols.remove('number')
industry_cols.remove('item')

for c in industry_cols:
    irs_is_statements_df[c] = \
        irs_is_statements_df[c].apply(
            lambda x: str(x).replace('[', '').replace(']', ''))

irs_is_statements_df[industry_cols] = irs_is_statements_df[industry_cols].astype(float)

irs_is_share_map = {}
for i in [33, 46, 47, 48, 50]:
    irs_is_share_map[i] = irs_is_statements_df[irs_is_statements_df.number.astype(str) == str(i)][industry_cols].sum()

share_46 = irs_is_share_map[46] / irs_is_share_map[33]
share_47 = irs_is_share_map[47] / irs_is_share_map[33]
share_48 = irs_is_share_map[48] / irs_is_share_map[33]
share_50 = irs_is_share_map[50] / irs_is_share_map[33]


def get_cost_of_goods_sold(irs_sector: str) -> float:
    irs_sector_clean = irs_sector.strip().replace('  ', ' ').lower()
    return share_46[irs_sector_clean] if irs_sector_clean in share_46 else share_46['all industries total']


def get_salaries_and_wages(irs_sector: str) -> float:
    irs_sector_clean = irs_sector.strip().replace('  ', ' ').lower()
    return share_48[irs_sector_clean] if irs_sector_clean in share_48 else share_48['all industries total']


def get_other_above_the_line_costs(irs_sector: str) -> float:
    irs_sector_clean = irs_sector.strip().replace('  ', ' ').lower()
    _47 = share_47[irs_sector_clean] if irs_sector_clean in share_47 else share_47['all industries total']
    _50 = share_50[irs_sector_clean] if irs_sector_clean in share_50 else share_50['all industries total']
    return _50 + _47