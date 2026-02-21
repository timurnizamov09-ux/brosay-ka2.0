import telebot
from telebot import types
import datetime
import random
import requests
import os
import json
import threading
import time
import schedule
from collections import defaultdict

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

# ================= ХРАНИЛИЩЕ =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_stats, f, ensure_ascii=False, indent=2)

user_stats = load_data()

def get_user(user_id):
    if str(user_id) not in user_stats:
        user_stats[str(user_id)] = {
            "motiv_count": 0,
            "facts": 0,
            "quit_start": None,
            "pack_price": None,
            "cigs_per_day": None,
            "saved_money": 0,
            "reminder": False
        }
    return user_stats[str(user_id)]

# ================= ФАКТЫ =================
FACTS = [
    "🧪 Никотин вызывает зависимость быстрее героина",
    "🧪 Курение сокращает жизнь на 10 лет",
    "🧪 Через 72 часа без сигарет улучшается дыхание",
    "🧪 Пассивное курение опасно"
]

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🌟 Мотиватор", "🎲 Факт")
    kb.add("💰 Экономия", "📊 Статистика")
    kb.add("📘 Советы", "⏰ Напоминания")
    kb.add("🤖 Спросить ИИ")

    bot.send_message(
        message.chat.id,
        "🌟 *Бросай-КА*\n\nЯ помогу тебе бросить курить 💪",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= ОБРАБОТКА =================
@bot.message_handler(func=lambda m: True)
def handler(message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    text = message.text
    user = get_user(uid)

    if text == "🌟 Мотиватор":
        msg = random.choice([
            "💪 Каждая минута без сигареты — победа",
            "❤️ Через год риск инфаркта снижается в 2 раза",
            "😎 Ты сильнее привычки"
        ])
        user["motiv_count"] += 1
        save_data()
        bot.send_message(chat_id, msg)

    elif text == "🎲 Факт":
        user["facts"] += 1
        save_data()
        bot.send_message(chat_id, random.choice(FACTS))

    elif text == "📊 Статистика":
        quit_days = 0
        if user["quit_start"]:
            quit_days = (datetime.date.today() -
                         datetime.date.fromisoformat(user["quit_start"])).days

        bot.send_message(
            chat_id,
            f"📊 *Твоя статистика*\n\n"
            f"🌟 Мотиваторов: {user['motiv_count']}\n"
            f"🎲 Фактов: {user['facts']}\n"
            f"🚭 Без сигарет: {quit_days} дней\n"
            f"💰 Сэкономлено: {user['saved_money']:.0f} ₽",
            parse_mode="Markdown"
        )

    elif text == "💰 Экономия":
        msg = bot.send_message(chat_id, "💰 Сколько стоит пачка сигарет? (в рублях)")
        bot.register_next_step_handler(msg, set_price)

    elif text == "📘 Советы":
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("Первый день", callback_data="tip1"),
            types.InlineKeyboardButton("Когда тянет", callback_data="tip2"),
            types.InlineKeyboardButton("Ошибки", callback_data="tip3"),
            types.InlineKeyboardButton("Мотивация", callback_data="tip4"),
        )
        bot.send_message(chat_id, "📘 *Полезные советы*", reply_markup=kb, parse_mode="Markdown")

    elif text == "⏰ Напоминания":
        user["reminder"] = not user["reminder"]
        save_data()
        status = "включены" if user["reminder"] else "выключены"
        bot.send_message(chat_id, f"⏰ Напоминания {status}")

    else:
        bot.send_chat_action(chat_id, "typing")
        bot.send_message(chat_id, "🤖 Я рядом, ты справишься 💪")

# ================= ЭКОНОМИЯ =================
def set_price(message):
    uid = str(message.from_user.id)
    try:
        price = float(message.text)
        user_stats[uid]["pack_price"] = price
        msg = bot.send_message(message.chat.id, "🚬 Сколько сигарет в день?")
        bot.register_next_step_handler(msg, set_cigs)
    except:
        bot.send_message(message.chat.id, "❌ Введи число")

def set_cigs(message):
    uid = str(message.from_user.id)
    try:
        cigs = int(message.text)
        user = user_stats[uid]
        user["cigs_per_day"] = cigs
        user["quit_start"] = datetime.date.today().isoformat()
        save_data()
        bot.send_message(message.chat.id, "✅ Отлично! Я начал считать твою экономию 💰")
    except:
        bot.send_message(message.chat.id, "❌ Введи число")

# ================= СОВЕТЫ =================
@bot.callback_query_handler(func=lambda c: True)
def tips(call):
    tips = {
        "tip1": "☀️ Первый день: пей воду, избегай кофе, дыши глубоко",
        "tip2": "😫 Тяга длится 3–5 минут — пережди её",
        "tip3": "🚫 Не пей алкоголь в первую неделю",
        "tip4": "🏆 Ты уже сделал важный шаг — не останавливайся"
    }
    bot.send_message(call.message.chat.id, tips.get(call.data, ""))

# ================= НАПОМИНАНИЯ =================
def daily_job():
    for uid, user in user_stats.items():
        if user.get("reminder") and user.get("quit_start"):
            days = (datetime.date.today() -
                    datetime.date.fromisoformat(user["quit_start"])).days

            if user.get("pack_price") and user.get("cigs_per_day"):
                daily = user["pack_price"] / 20 * user["cigs_per_day"]
                user["saved_money"] = daily * days

            bot.send_message(
                int(uid),
                f"⏰ Напоминание\n\n🚭 Ты без сигарет уже {days} дней\n💰 Сэкономил: {user['saved_money']:.0f} ₽"
            )
    save_data()

schedule.every().day.at("20:00").do(daily_job)

def scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=scheduler, daemon=True).start()

# ================= ЗАПУСК =================
print("✅ БОТ ОНЛАЙН 24/7")
bot.infinity_polling(skip_pending=True)
