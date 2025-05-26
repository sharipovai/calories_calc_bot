import sqlite3
import pandas as pd
import config

def get_stat():
    database = config.database_path
    conn = sqlite3.connect(database)
    script = "SELECT * FROM statistics"
    df = pd.read_sql_query(script, conn)
    df['user_count'] = 0
    cnt = 0
    number = 1
    start_cnt = 0
    for index, row in df.iterrows():
        cnt += row['new_user']
        df.loc[index, 'user_count'] = start_cnt + cnt
        df.loc[index, 'number'] = number
        number += 1
    df = df.sort_values('number', ascending=False)
    df = df.drop(columns=['number'])
    df.to_excel("./statistics.xlsx", index=False)
    script = "SELECT * FROM user_information"
    df2 = pd.read_sql_query(script, conn)
    df2.to_excel("./users_information.xlsx", index=False)
    return start_cnt + cnt
