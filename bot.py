import telebot
from telebot import types
import datetime
import random
import requests
import os
from collections import defaultdict

# ========== НАСТРОЙКИ (через переменные окружения) ==========
TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения")

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = telebot.TeleBot(TOKEN)

# ========== ХРАНИЛИЩА ==========
user_data = {}
chat_history = defaultdict(list)
motiv_shown = defaultdict(list)

user_stats = defaultdict(lambda: {
    'motiv_count': 0,
    'tests_completed': 0,
    'facts_shown': 0,
    'quit_start': None,
    'achievements': [],
    'savings_total': 0,
    'last_active': None
})

# ========== ДОСТИЖЕНИЯ ==========
ACHIEVEMENTS = {
    'first_motiv': ('🌱 Первый шаг', 'Посмотрел первый мотиватор'),
    'motiv_10': ('🚶 На пути', '10 мотиваторов'),
    'first_test': ('🧠 Самопознание', 'Пройден тест'),
}

# ========== ФАКТЫ ==========
SCIENCE_FACTS = [
    "🧪 В табачном дыме более 70 канцерогенов.",
    "🧪 Никотин вызывает зависимость быстрее героина.",
    "🧪 Курение сокращает жизнь в среднем на 10 лет.",
    "🧪 Уже через 72 часа без курения улучшается дыхание.",
]

# ========== ИИ ==========
def get_ai_response(user_id, text):
    if not OPENROUTER_API_KEY:
        return "⚠️ ИИ временно недоступен."

    chat_history[user_id].append({"role": "user", "content": text})
    chat_history[user_id] = chat_history[user_id][-5:]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {"role": "system", "content": "Ты дружелюбный помощник по отказу от курения. Кратко и поддерживающе."},
            *chat_history[user_id]
        ],
        "max_tokens": 200
    }

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=20
        )
        if r.status_code == 200:
            answer = r.json()["choices"][0]["message"]["content"]
            chat_history[user_id].append({"role": "assistant", "content": answer})
            return answer
        return "😔 Ошибка ИИ."
    except:
        return "😔 ИИ временно недоступен."

# ========== ДОСТИЖЕНИЯ ==========
def check_achievements(user_id, chat_id):
    stats = user_stats[user_id]

    if stats['motiv_count'] >= 1 and 'first_motiv' not in stats['achievements']:
        stats['achievements'].append('first_motiv')
        bot.send_message(chat_id, "🏆 Достижение: 🌱 Первый шаг")

    if stats['motiv_count'] >= 10 and 'motiv_10' not in stats['achievements']:
        stats['achievements'].append('motiv_10')
        bot.send_message(chat_id, "🏆 Достижение: 🚶 На пути")

    if stats['tests_completed'] >= 1 and 'first_test' not in stats['achievements']:
        stats['achievements'].append('first_test')
        bot.send_message(chat_id, "🏆 Достижение: 🧠 Самопознание")

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_stats[user_id]['last_active'] = datetime.datetime.now()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🌟 Мотиватор", "🎲 Факт")
    kb.add("📊 Статистика", "🤖 Спросить ИИ")

    bot.send_message(
        message.chat.id,
        "🌟 *Бросай-КА*\n\nЯ помогу тебе бросить курить 💪",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ========== КНОПКИ ==========
@bot.message_handler(func=lambda m: True)
def handler(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    user_stats[user_id]['last_active'] = datetime.datetime.now()

    if text == "🌟 Мотиватор":
        motiv = random.choice([
            "💪 Каждая минута без сигареты — победа.",
            "❤️ Через год риск инфаркта снижается в 2 раза.",
            "😎 Ты сильнее привычки."
        ])
        user_stats[user_id]['motiv_count'] += 1
        check_achievements(user_id, chat_id)
        bot.send_message(chat_id, motiv)

    elif text == "🎲 Факт":
        user_stats[user_id]['facts_shown'] += 1
        bot.send_message(chat_id, random.choice(SCIENCE_FACTS))

    elif text == "📊 Статистика":
        stats = user_stats[user_id]
        bot.send_message(
            chat_id,
            f"📊 Статистика:\n"
            f"🌟 Мотиваторов: {stats['motiv_count']}\n"
            f"🎲 Фактов: {stats['facts_shown']}\n"
            f"🏆 Достижений: {len(stats['achievements'])}"
        )

    else:
        bot.send_chat_action(chat_id, 'typing')
        bot.send_message(chat_id, get_ai_response(user_id, text))

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("✅ БОТ ОНЛАЙН 24/7")
    bot.infinity_polling(skip_pending=True)
