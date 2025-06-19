import os
import config
from telebot import types
import telebot
from database import *
from statistics import get_stat
from google import genai
from pyzbar.pyzbar import decode
from PIL import Image


client = genai.Client(api_key=config.api_key)

db = Database(config.database_path)
bot_token = config.prod_bot_token
bot = telebot.TeleBot(bot_token)

CHAT_BY_DATETIME = dict()
LAST_QUERY = datetime.now()
QUERY_COUNT = 0


def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def check_query_cnt():
    error = 0
    global LAST_QUERY
    global QUERY_COUNT
    current_time = datetime.now()
    delta_seconds = (current_time - LAST_QUERY).total_seconds()
    if QUERY_COUNT > 14 and delta_seconds < 60:
        error = 1
    elif delta_seconds > 60:
        LAST_QUERY = current_time
        QUERY_COUNT = 1
    else:
        QUERY_COUNT += 1
    return error

def check_time(message):
    current_time = datetime.now()
    error = 0
    last_datetime = CHAT_BY_DATETIME.get(message.chat.id)
    if not last_datetime:
        CHAT_BY_DATETIME[message.chat.id] = current_time
    else:
        delta_seconds = (current_time - last_datetime).total_seconds()
        CHAT_BY_DATETIME[message.chat.id] = current_time
        if delta_seconds < 2:
            error = 1
    return error

def add_food_from_code(message, meal_type):
    code = get_code(message)
    if code == 0:
        bot.send_message(message.chat.id, f'Не удалось считать штрихкод по фото. Введите штрихкод')
        return bot.register_next_step_handler(message, read_new_product_code, meal_type)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Да')
    btn2 = types.KeyboardButton('Нет')
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, f'Штрхкод {code}, верно?', reply_markup=markup)
    return bot.register_next_step_handler(message, add_food_from_code2, code, meal_type)

def add_food_from_code2(message, code, meal_type):
    if message.text is None:
        bot.send_message(message.chat.id, f'Если штрихкод верный введите "да" или в противном случае введите "нет"')
        return bot.register_next_step_handler(message, add_food_from_code2, meal_type)
    elif message.text == '/start':
        return start(message)
    if 'нет' in message.text.lower():
        bot.send_message(message.chat.id, f'Введите правильный штрихкод')
        return bot.register_next_step_handler(message, read_new_product_code, meal_type)
    else:
        return add_food_from_code3(message, code, meal_type)


def add_food_from_code3(message, code, meal_type):
    check_flag = db.check_new_food_code(code)
    if check_flag == 0:
        product_info = db.get_food_info_from_code(code)
        add_food_from_code5(message, product_info, meal_type)
    else:
        bot.send_message(message.chat.id, f'Шрихкод не найден в базе данных. Введите название продукта.')
        product_info = {'Наименование': "", 'Калорийность': 0, 'Белки': 0, 'Жиры': 0, 'Углеводы': 0}
        bot.register_next_step_handler(message, add_food_from_code4, product_info, 1, code, meal_type)


def add_food_from_code4(message, product_info, step, code, meal_type):
    d = {1: ["Введите название продукта.", 'Наименование'],
         2: ["Введите количество белков в 100г продукта", 'Белки'],
         3: ["Введите количество жиров в 100г продукта", 'Жиры'],
         4: ["Введите количество углеводов в 100г продукта", 'Углеводы'],
         5: ["Введите калорийность на 100г продукта", 'Калорийность']}
    if message.text is None:
        bot.send_message(message.chat.id, f'Текст сообщения пустой. {d[step][0]}')
        return bot.register_next_step_handler(message, add_food_from_code4, product_info, step, code, meal_type)
    elif message.text == '/start':
        return start(message)
    elif step in [2, 3, 4, 5] and is_float(message.text) is False:
        bot.send_message(message.chat.id, f'Должно быть число. Попробуйте еще раз. {d[step][0]}')
        return bot.register_next_step_handler(message, add_food_from_code4, product_info, step, code, meal_type)
    elif step < 5:
        if step == 1:
            product_info[d[step][1]] = message.text
        else:
            product_info[d[step][1]] = float(message.text)
        step += 1
        bot.send_message(message.chat.id, f'{d[step][0]}')
        return bot.register_next_step_handler(message, add_food_from_code4, product_info, step, code, meal_type)
    else:
        product_info[d[step][1]] = int(message.text)
        db.add_new_food_code(code, food_name=product_info[d[1][1]], protein=product_info[d[2][1]],
                             carbohydrates=product_info[d[4][1]], fats=product_info[d[3][1]],
                             total_calories=product_info[d[5][1]])
        bot.send_message(message.chat.id, f'Продукт добавлен в базу данных!')
        return add_food_from_code5(message, product_info, meal_type)


def add_food_from_code5(message, product_info, meal_type):
    bot.send_message(message.chat.id, f'Введите вес вашей порции данного продукта в граммах')
    return bot.register_next_step_handler(message, add_food_from_code6, product_info, meal_type)

def add_food_from_code6(message, product_info, meal_type):
    if message.text is None or message.text.isdigit() is False:
        bot.send_message(message.chat.id, f'Должно быть целое число')
        return add_food_from_code5(message, product_info, meal_type)
    elif message.text == '/start':
        return start(message)
    else:
        weight = int(message.text)
        protein = int(weight * product_info['Белки'] / 100)
        fat = int(weight * product_info['Жиры'] / 100)
        carbonates = int(weight * product_info['Углеводы'] / 100)
        calories = int(weight * product_info['Калорийность'] / 100)
        result = {'Наименование': product_info['Наименование'], 'Калорийность': calories, 'Белки': protein,
                'Жиры': fat, 'Углеводы': carbonates}
        return add_food_to_db1(message, result, meal_type)


def read_new_product_code(message, meal_type):
    if message.text is None:
        bot.send_message(message.chat.id, f'Текст сообщения пустой. Введите правильный штрихкод')
        return bot.register_next_step_handler(message, read_new_product_code, meal_type)
    elif message.text == '/start':
        return start(message)
    elif message.text.isdigit() is False:
        bot.send_message(message.chat.id, f'Штрихкод должен быть числом. Введите правильный штрихкод')
        return bot.register_next_step_handler(message, read_new_product_code, meal_type)
    else:
        code = int(message.text)
        return add_food_from_code3(message, code, meal_type)

def get_code(message):
    if message.content_type != 'photo':
        return 0
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Сохраняем файл временно
    temp_path = f"./{message.from_user.id}.jpg"
    with open(temp_path, 'wb') as f:
        f.write(downloaded_file)

    image = Image.open(temp_path)  # путь к твоему изображению
    os.remove(temp_path)

    # Распознать штрихкод
    decoded_objects = decode(image)
    try:
        code = int(decoded_objects[0].data.decode('utf-8'))
    except Exception as e:
        print(e)
        code = 0
    return code


def parse_nutrition(text):
    name, calories, protein, fat, carbonates = "", 0, 0, 0, 0
    try:
        splitted_text = [i.strip() for i in text.split(":")]
        protein_indx = 2
        for i, text in enumerate(splitted_text[1:-2]):
            if 'белок' in text.lower() or 'белк' in text.lower():
                protein_indx = i+1
        for i, t in enumerate(splitted_text):
            splitted_text[i] = t.replace("\n", ",").replace(".", ",").replace("~", "").replace("*", "")

        name = splitted_text[protein_indx-1].split(",")[0]
        calories = splitted_text[protein_indx].split(" ")[0]
        protein = splitted_text[protein_indx+1].split(" ")[0]
        fat = splitted_text[protein_indx+2].split(" ")[0]
        carbonates = splitted_text[protein_indx+3].split(" ")[0]
    except Exception as e:
        print(e)

    return {'Наименование': name, 'Калорийность': calories, 'Белки': protein, 'Жиры': fat, 'Углеводы': carbonates}

def write_statistics(statistics_type, user_id):
    now = datetime.now().strftime("%d.%m.%y")
    date_list = db.get_date_str_statistics()
    if now not in date_list:
        db.write_new_date_statistics()
    db.write_statistics(statistics_type, user_id)


@bot.message_handler(commands=['start'])
def start(message):
    db.create_db()
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!')
    if db.check_new_user(message.from_user.id):
        db.write_new_user(message)
        write_statistics("new_user", message.from_user.id)
        bot.send_message(message.chat.id, f'{config.hello_message}')
    return wait_command(message)


@bot.message_handler(commands=['stat'])
def stat(message):
    if message.from_user.id == config.admin_tg_id:
        cnt = get_stat()
        bot.send_message(message.chat.id, f'Всего пользователей {cnt}')
        bot.register_next_step_handler(message, stat_step2)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn1 = types.KeyboardButton('Да')
        btn2 = types.KeyboardButton('Нет')
        markup.row(btn1, btn2)
        bot.send_message(message.chat.id, f'Хотите получить полную статистику по боту?', reply_markup=markup)


def stat_step2(message):
    if 'да' in message.text.lower():
        with open("./statistics.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
        with open("./users_information.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
        with open("./payments.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
    return wait_command(message)


@bot.message_handler(commands=['newsletter'])
def newsletter(message):
    if message.from_user.id == config.admin_tg_id:
        bot.send_message(message.chat.id, f'Введи текст рассылки!')
        bot.register_next_step_handler(message, newsletter_step2)


def newsletter_step2(message):
    text = message.text
    chat_id_list = db.get_user_id_list()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Сделать рассылку')
    btn2 = types.KeyboardButton('Отмена')
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, f'Количество получателей: {len(chat_id_list)}. Им будет направлена следующая рассылка:\n{text}', reply_markup=markup)
    bot.register_next_step_handler(message, newsletter_step3, chat_id_list, text)


def newsletter_step3(message, chat_id_list, text):
    if 'сделать рассылку' in message.text.lower():
        if len(chat_id_list) > 0:
            for chat_id in chat_id_list:
                try:
                    bot.send_message(chat_id, text)
                except Exception as e:
                    print("Произошла ошибка:", e)
        else:
            bot.send_message(message.chat.id, f'Отсутствуют получатели, рассылка невозможна')
    elif message.text.lower() != "отмена":
        bot.send_message(message.chat.id, f'Неизвестная команда')
    return wait_command(message)


def wait_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(f'Добавить еду')
    btn2 = types.KeyboardButton(f'Питание сегодня')
    btn3 = types.KeyboardButton('Все мое питание')
    markup.row(btn1)
    markup.row(btn2)
    markup.row(btn3)
    bot.send_message(message.chat.id, f'Выбери команду', reply_markup=markup)
    bot.register_next_step_handler(message, wait_command1)


@bot.message_handler()
def wait_command1(message):
    if message.text is None:
        return wait_command(message)
    elif message.text.lower() == '/start':
        return start(message)
    elif message.text.lower() == '/newsletter':
        return newsletter(message)
    elif message.text.lower() == '/stat':
        return stat(message)
    elif message.text.lower() == 'питание сегодня':
        today_food = db.get_today_food_information(message.from_user.id)
        text = ""
        for data in today_food:
            for key, value in data.items():
                text +=f"{key}: {value}\n"
            text += "\n"
        bot.send_message(message.chat.id, f'Вы сегодня съели:\n{text}')
        return wait_command(message)
    elif message.text.lower() == 'все мое питание':
        result = db.get_total_food_information(message.from_user.id)
        file_name = f"./{message.from_user.id}.xlsx"
        result.to_excel(file_name, index=False)
        with open(file_name, 'rb') as f:
            bot.send_document(message.chat.id, f)
        os.remove(file_name)
        return wait_command(message)
    elif message.text.lower() == 'добавить еду':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for meal in config.meals_types:
            btn0 = types.KeyboardButton(meal)
            markup.row(btn0)
        bot.send_message(message.chat.id, f'Выбери какой прием пищи хочешь добавить',reply_markup=markup)
        bot.register_next_step_handler(message, wait_command2)
    else:
        bot.send_message(message.chat.id, f'Ошибка! Введено неверное значение.')
        return wait_command(message)

def wait_command2(message):
    if message.text is None:
        return wait_command(message)
    elif message.text.lower() == '/start':
        return start(message)
    elif message.text.lower() in config.meals_types:
        meal_type = message.text.lower()
        return wait_command3(message, meal_type)
    else:
        bot.send_message(message.chat.id, f'Ошибка! Введено неверное значение. Выбери из {config.meals_types}')
        return wait_command(message)


def wait_command3(message, meal_type):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn0 = types.KeyboardButton(f'Штрхкод')
    btn1 = types.KeyboardButton(f'Фото')
    btn2 = types.KeyboardButton(f'Текст')
    markup.row(btn0)
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, f'Выбери способ добавления информации о приеме пищи',
                     reply_markup=markup)
    bot.register_next_step_handler(message, info, meal_type)

def info(message, meal_type):
    if message.text is None:
        return wait_command3(message, meal_type)
    elif message.text.lower() == 'фото':
        bot.send_message(message.chat.id, f'Загрузите фото приема пищи')
        bot.register_next_step_handler(message, get_food_photo, meal_type)
    elif message.text.lower() == '/start':
        return start(message)
    elif message.text.lower() == 'штрхкод':
        bot.send_message(message.chat.id, f'Сфотографируй штрихкод продукта')
        return bot.register_next_step_handler(message, add_food_from_code, meal_type)
    elif message.text.lower() == 'текст':
        mes = bot.send_message(message.chat.id, f'Пожалуйста подождите')
        return llm_text(message, mes, meal_type)
    else:
        bot.send_message(message.chat.id, 'Ошибка! Неверная команда')
        return wait_command3(message, meal_type)

def get_food_photo(message, meal_type):
    if message.content_type == 'photo':
        mes = bot.send_message(message.chat.id, f'Пожалуйста подождите')
        return llm_photo(message, mes, meal_type)
    else:
        bot.send_message(message.chat.id, 'Ошибка! Фото не найдено.')
        return wait_command3(message, meal_type)


def llm_photo(message, mes, meal_type):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Сохраняем файл временно
    temp_path = f"./{message.from_user.id}.jpg"
    with open(temp_path, 'wb') as f:
        f.write(downloaded_file)

    # Загружаем в Gemini
    gemini_file = client.files.upload(file=temp_path)
    os.remove(temp_path)

    # Отправляем запрос
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            gemini_file,
            config.img_prompt  # или config.prompt
        ]
    )
    result = parse_nutrition(response.text)
    bot.delete_message(message.chat.id, mes.id)
    if result['Наименование'] == "":
        bot.send_message(message.chat.id, 'Ошибка получения данных. Попробуйте позже.')
        print(f"Не удалось распарсить строку. {response.text}")
    else:
        add_food_to_db1(message, result, meal_type)

def llm_text(message, mes, meal_type):
    # Отправляем запрос
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            config.txt_prompt+message.text  # или config.prompt
        ]
    )
    result = parse_nutrition(response.text)
    bot.delete_message(message.chat.id, mes.id)
    if result['Наименование'] == "":
        bot.send_message(message.chat.id, 'Ошибка получения данных. Попробуйте позже.')
        print(f"Не удалось распарсить строку. {response.text}")
    else:
        add_food_to_db1(message, result, meal_type)


def add_food_to_db1(message, result, meal_type):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton(f'Да')
    btn2 = types.KeyboardButton('Нет')
    markup.row(btn1, btn2)
    text = "\n".join(f"{k}: {v}" for k, v in result.items())
    bot.send_message(message.chat.id, f'{text}\nДобавить?',
                     reply_markup=markup)
    bot.register_next_step_handler(message, add_food_to_db2, result, meal_type)


def add_food_to_db2(message, result, meal_type):
    if message.text is not None and message.text.lower() == 'да':
        db.add_new_food(message.from_user.id, type_of_meal=meal_type, food_name=result['Наименование'],
                        protein=result['Белки'], carbohydrates=result['Углеводы'], fats=result['Жиры'],
                        total_calories=result['Калорийность'])
        bot.send_message(message.chat.id, f'Еда успешно добавлена!')
        return wait_command(message)
    elif message.text is not None and message.text.lower() == 'нет':
        bot.send_message(message.chat.id, f'Еда не добавлена.')
        return wait_command(message)
    else:
        add_food_to_db1(message, result, meal_type)







bot.infinity_polling()