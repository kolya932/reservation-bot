import telebot
import os
import sqlite3
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
user_data = {}

# БД
conn = sqlite3.connect('bookings.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        name TEXT,
        people INTEGER,
        date TEXT,
        time TEXT,
        table_number INTEGER
    )
''')
conn.commit()

MAX_TABLES = 10

# Меню
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Забронювати столик")
    markup.add("🔍 Переглянути бронювання")
    markup.add("🏠 Інформація про заклад")
    markup.add("📞 Контакти", "❌ Скасувати запис")
    return markup

def cancel_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("⬅️ Назад", "❌ Скасувати запис")
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Привіт! Я бот для бронювання столиків. Оберіть опцію нижче 👇", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📅 Забронювати столик")
def handle_booking(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    bot.send_message(chat_id, "Введіть ваше повне ПІБ:", reply_markup=cancel_button())
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    if message.text == "❌ Скасувати запис":
        return cancel_booking(message)
    elif message.text == "⬅️ Назад":
        return start_message(message)

    chat_id = message.chat.id
    user_data[chat_id]["name"] = message.text
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("1", "2", "3", "4", "5+")
    markup.add("⬅️ Назад", "❌ Скасувати запис")
    bot.send_message(chat_id, "На скільки осіб бронювання?", reply_markup=markup)
    bot.register_next_step_handler(message, get_people)

def get_people(message):
    if message.text == "❌ Скасувати запис":
        return cancel_booking(message)
    elif message.text == "⬅️ Назад":
        return handle_booking(message)

    chat_id = message.chat.id
    try:
        user_data[chat_id]["people"] = int(message.text.replace("+", ""))
        bot.send_message(chat_id, "Введіть дату (у форматі ДД.ММ):", reply_markup=cancel_button())
        bot.register_next_step_handler(message, get_date)
    except:
        bot.send_message(chat_id, "Будь ласка, введіть число")
        bot.register_next_step_handler(message, get_people)

def get_date(message):
    if message.text == "❌ Скасувати запис":
        return cancel_booking(message)
    elif message.text == "⬅️ Назад":
        return get_name(message)

    chat_id = message.chat.id
    user_data[chat_id]["date"] = message.text
    bot.send_message(chat_id, "Введіть час (наприклад, 18:00):", reply_markup=cancel_button())
    bot.register_next_step_handler(message, get_time)

def get_time(message):
    if message.text == "❌ Скасувати запис":
        return cancel_booking(message)
    elif message.text == "⬅️ Назад":
        return get_people(message)

    chat_id = message.chat.id
    time = message.text
    date = user_data[chat_id]["date"]

    c.execute("SELECT COUNT(*) FROM bookings WHERE date = ? AND time = ?", (date, time))
    count = c.fetchone()[0]

    if count >= MAX_TABLES:
        bot.send_message(chat_id, "⛔ У цей час вже всі столики зайняті. Спробуйте інший час або дату.", reply_markup=main_menu())
        return

    table_number = count + 1
    user_data[chat_id]["time"] = time
    user_data[chat_id]["table_number"] = table_number

    c.execute("INSERT INTO bookings (chat_id, name, people, date, time, table_number) VALUES (?, ?, ?, ?, ?, ?)",
              (chat_id, user_data[chat_id]["name"], user_data[chat_id]["people"], date, time, table_number))
    conn.commit()

    bot.send_message(chat_id, f"✅ Столик заброньовано на {date} о {time}. Номер столика: {table_number}", reply_markup=main_menu())
    user_data.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "🔍 Переглянути бронювання")
def view_bookings(message):
    chat_id = message.chat.id
    c.execute("SELECT name, date, time, table_number FROM bookings WHERE chat_id = ?", (chat_id,))
    rows = c.fetchall()
    if not rows:
        bot.send_message(chat_id, "У вас немає активних бронювань.")
    else:
        msg = "Ваші бронювання:\n"
        for row in rows:
            msg += f"👤 {row[0]} | 📅 {row[1]} | 🕒 {row[2]} | № столика: {row[3]}\n"
        bot.send_message(chat_id, msg)

@bot.message_handler(func=lambda m: m.text == "🏠 Інформація про заклад")
def about_place(message):
    bot.send_message(message.chat.id, "Наш заклад працює щодня з 10:00 до 22:00. 🍽️ Запрошуємо вас смачно провести час!")

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def contact_info(message):
    bot.send_message(message.chat.id, "Телефон: +380000000000 \nInstagram: @our_cafe")

@bot.message_handler(func=lambda m: m.text == "❌ Скасувати запис")
def cancel_booking(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    c.execute("DELETE FROM bookings WHERE chat_id = ?", (chat_id,))
    conn.commit()
    bot.send_message(chat_id, "❌ Запис скасовано. Ви повернулись у головне меню.", reply_markup=main_menu())

bot.polling(none_stop=True)
