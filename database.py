import sqlite3
from collections import defaultdict
from datetime import datetime
import pandas as pd

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    def create_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS user_information (user_id int primary_key, user_name varchar(50), "
            "first_name varchar(50), registration_date varchar(50))")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS statistics (number INTEGER PRIMARY KEY AUTOINCREMENT, date varchar(20), "
            "user_id varchar(5000), new_user int, unique_users int)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS food (food_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id int, type_of_meal "
            "varchar(50), food_name varchar(50), protein int, carbohydrates int, fats int, total_calories int, "
            "date varchar(20))")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS food_codes (code INTEGER PRIMARY KEY, "
            "food_name varchar(50), protein real, carbohydrates real, fats real, total_calories real, date varchar(20))")
        conn.commit()
        cur.close()
        conn.close()

    def write_statistics(self, parameter_name, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = (datetime.now()).strftime("%d.%m.%y")
        count = cur.execute(f"SELECT {parameter_name} FROM statistics WHERE date = '%s'"
                                         % today_date).fetchall()[0][0]
        count += 1
        cur.execute(f"UPDATE statistics SET {parameter_name}  = %d WHERE date = '%s'" % (count, today_date))
        conn.commit()
        user_id_str = str(cur.execute("SELECT user_id FROM statistics WHERE date = '%s'"
                                         % today_date).fetchall()[0][0])
        if str(user_id) not in user_id_str:
            user_id_str = str(user_id_str + "n" + str(user_id))
            cur.execute("UPDATE statistics SET user_id = ? WHERE date = ?", (user_id_str, today_date))
            conn.commit()
            unique_users = int(cur.execute("SELECT unique_users FROM statistics WHERE date = '%s'"
                                    % today_date).fetchall()[0][0])
            unique_users += 1
            cur.execute("UPDATE statistics SET unique_users = '%d' WHERE date = '%s'" % (unique_users, today_date))
            conn.commit()
        cur.close()
        conn.close()

    def get_date_str_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT date FROM statistics").fetchall()
        if len(result) > 0:
            result_list = [i[0] for i in result]
        else:
            result_list = []
        cur.close()
        conn.close()
        return result_list

    def write_new_date_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = (datetime.now()).strftime("%d.%m.%y")
        cur.execute("INSERT INTO statistics (date, user_id, new_user, unique_users) VALUES "
                    "('%s', '%d', '%d', '%d')" % (today_date, 0, 0, 0))
        conn.commit()
        cur.close()
        conn.close()

    def check_new_user(self, user_id):
        # for new user return 1
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM user_information WHERE user_id = '%d'" % user_id).fetchall()
        cur.close()
        conn.close()
        return not bool(len(result))

    def write_new_user(self, message):
        if not self.check_new_user(message.from_user.id):
            return
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        reg_date = (datetime.now()).strftime("%d.%m.%y")
        cur.execute("INSERT INTO user_information (user_id, user_name, first_name, registration_date)"
                    " VALUES ('%d', '%s','%s', '%s')" % (message.from_user.id,
                                                         message.from_user.username,
                                                         message.from_user.first_name, reg_date))
        conn.commit()
        cur.close()
        conn.close()

    def get_user_parameter(self, user_id, parameter_name):
        # return parameter value
        parameters = ["user_name", "first_name", "registration_date"]
        parameter_value = 0
        if parameter_name in parameters:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            parameter_value = cur.execute(f"SELECT {parameter_name} FROM user_information WHERE user_id = '%d'"
                                          % user_id).fetchall()[0][0]
            cur.close()
            conn.close()
        return parameter_value

    def get_user_id_list(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        chat_id_tuple = cur.execute(f"SELECT user_id FROM user_information").fetchall()
        chat_id_list = [i1[0] for i1 in chat_id_tuple if i1[0] != 0]
        cur.close()
        conn.close()
        return chat_id_list

    def add_new_food(self, user_id, type_of_meal, food_name, protein, carbohydrates, fats, total_calories):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = datetime.now().strftime("%d.%m.%y")
        cur.execute(
            "INSERT INTO food (user_id, type_of_meal, food_name, protein, carbohydrates, fats, total_calories, date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, type_of_meal, food_name, protein, carbohydrates, fats, total_calories, today_date)
        )
        conn.commit()
        cur.close()
        conn.close()

    def add_new_food_code(self, code, food_name, protein, carbohydrates, fats, total_calories):
        if self.check_new_food_code(code) == 1:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            today_date = datetime.now().strftime("%d.%m.%y")
            cur.execute(
                "INSERT INTO food_codes (code, food_name, protein, carbohydrates, fats, total_calories, date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (code, food_name, protein, carbohydrates, fats, total_calories, today_date)
            )
            conn.commit()
            cur.close()
            conn.close()

    def check_new_food_code(self, code):
        # for new code return 1
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM food_codes WHERE code = '%d'" % code).fetchall()
        cur.close()
        conn.close()
        return not bool(len(result))

    def get_food_info_from_code(self, code):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT food_name, protein, carbohydrates, fats, total_calories FROM "
                             "food_codes WHERE code = ?", (code, )).fetchall()[0]
        cur.close()
        conn.close()
        product_info = {'Наименование': result[0], 'Калорийность': result[4], 'Белки': result[1], 'Жиры': result[3],
                        'Углеводы': result[2]}
        return product_info

    def get_today_food_information(self, user_id):
        conn = sqlite3.connect(self.db_path)
        today_date = datetime.now().strftime("%d.%m.%y")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        result = cur.execute("SELECT food_name, type_of_meal, protein, carbohydrates, fats, total_calories FROM "
                             "food WHERE user_id = ? AND date = ?", (user_id, today_date)).fetchall()
        cur.close()
        conn.close()
        renamed = defaultdict(list)
        for row in result:
            renamed[row["type_of_meal"]].append({
                "Наименование": row["food_name"],
                "Белки": str(row["protein"]) + " г.",
                "Углеводы": str(row["carbohydrates"]) + " г.",
                "Жиры": str(row["fats"]) + " г.",
                "Калорийность": str(row["total_calories"]) + " ккал."
            })

        return renamed

    def get_total_food_information(self, user_id):
        conn = sqlite3.connect(self.db_path)
        script = f"SELECT * FROM food WHERE user_id = {user_id}"
        df = pd.read_sql_query(script, conn)
        user_df = df.loc[df['user_id'] == user_id]
        user_df = user_df.drop(columns=['user_id', 'food_id'])
        group_column = ['type_of_meal', 'date']
        result = user_df.groupby(group_column, as_index=False).agg({
            'food_name': lambda x: ', '.join(x),
            'protein': 'sum',
            'carbohydrates': 'sum',
            'fats': 'sum',
            'total_calories': 'sum'
        })
        conn.close()
        return result

