from collections import defaultdict

def create_df_dict(year, main_bol, final_append):
    df_dict = defaultdict(list)
    for i in range(year):
        df_dict["year"].append(i)
        if main_bol == "No":
            df_dict["value"].append(0)
        else:
            if i == 0:
                df_dict["value"].append(0)
            else:
                df_dict["value"].append(final_append)
    return df_dict