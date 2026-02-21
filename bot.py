import telebot
from telebot import types
import datetime
import random
import requests
import json
import os
from collections import defaultdict

# ========== НАСТРОЙКИ (ВАЖНО) ==========
TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в переменных окружения")

bot = telebot.TeleBot(TOKEN)

# ========== ХРАНИЛИЩА ДАННЫХ ==========
user_data = {}
chat_history = defaultdict(list)
motiv_shown = defaultdict(list)

user_stats = defaultdict(lambda: {
    'motiv_count': 0,
    'tests_completed': 0,
    'facts_shown': 0,
    'quit_days': 0,
    'quit_start': None,
    'achievements': [],
    'savings_total': 0,
    'challenge_with': None,
    'last_active': None
})

# ========== ДОСТИЖЕНИЯ ==========
ACHIEVEMENTS = {
    'first_motiv': {'name': '🌟 Первый шаг', 'desc': 'Посмотрел первый мотиватор'},
    'motiv_10': {'name': '🏃 На пути', 'desc': '10 мотиваторов'},
    'motiv_50': {'name': '🔥 Мотивированный', 'desc': '50 мотиваторов'},
    'first_test': {'name': '📝 Самопознание', 'desc': 'Прошёл тест'},
    'first_save': {'name': '💰 Экономный', 'desc': 'Посчитал траты'},
    'week_quit': {'name': '🎉 Неделя', 'desc': '7 дней без сигарет'},
    'month_quit': {'name': '👑 Герой', 'desc': '30 дней без сигарет'},
    'fact_master': {'name': '📚 Знаток', 'desc': '30 фактов'}
}

# ========== ФАКТЫ ==========
SCIENCE_FACTS = [
    "🧪 В табачном дыме более 70 канцерогенов.",
    "🧪 Никотин вызывает зависимость быстрее героина.",
    "🧪 Курение сокращает жизнь на 10 лет.",
    "🧪 Пассивное курение опасно.",
    "🧪 Уже через 72 часа без курения улучшается дыхание.",
] * 10

# ========== ИИ ==========
def get_ai_response(user_id, user_message):
    if not OPENROUTER_API_KEY:
        return "⚠️ ИИ временно недоступен."

    chat_history[user_id].append({"role": "user", "content": user_message})
    chat_history[user_id] = chat_history[user_id][-5:]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {
                "role": "system",
                "content": "Ты — дружелюбный помощник по отказу от курения. Отвечай кратко и поддерживающе."
            },
            *chat_history[user_id]
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            answer = response.json()["choices"][0]["message"]["content"]
            chat_history[user_id].append({"role": "assistant", "content": answer})
            return answer
        return "😔 Ошибка ИИ."
    except:
        return "😔 ИИ временно недоступен."

# ========== ДОСТИЖЕНИЯ ==========
def check_achievements(user_id, chat_id):
    stats = user_stats[user_id]

    for key, data in ACHIEVEMENTS.items():
        if key not in stats['achievements']:
            if key == 'first_motiv' and stats['motiv_count'] >= 1:
                pass
            elif key == 'motiv_10' and stats['motiv_count'] >= 10:
                pass
            elif key == 'motiv_50' and stats['motiv_count'] >= 50:
                pass
            elif key == 'first_test' and stats['tests_completed'] >= 1:
                pass
            elif key == 'first_save' and stats['savings_total'] > 0:
                pass
            elif key == 'fact_master' and stats['facts_shown'] >= 30:
                pass
            else:
                continue

            stats['achievements'].append(key)
            bot.send_message(
                chat_id,
                f"🏆 *Новое достижение!*\n{data['name']}\n_{data['desc']}_",
                parse_mode="Markdown"
            )

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        "🌟 Мотиватор дня", "🎲 Случайный факт",
        "📊 Моя статистика", "🏆 Достижения",
        "🤖 Спросить ИИ"
    )

    bot.send_message(
        message.chat.id,
        "🌟 *Бросай-КА 2.0*\n\nЯ помогу тебе бросить курить 💪",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@bot.message_handler(func=lambda message: True)
def handler(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    user_stats[user_id]['last_active'] = datetime.datetime.now()

    if text == "🌟 Мотиватор дня":
        motiv = random.choice([
            "💪 Каждая минута без сигареты — победа.",
            "❤️ Через год риск инфаркта снижается в 2 раза.",
            "😎 Ты сильнее привычки."
        ])
        user_stats[user_id]['motiv_count'] += 1
        check_achievements(user_id, chat_id)
        bot.send_message(chat_id, motiv)

    elif text == "🎲 Случайный факт":
        user_stats[user_id]['facts_shown'] += 1
        check_achievements(user_id, chat_id)
        bot.send_message(chat_id, random.choice(SCIENCE_FACTS))

    elif text == "📊 Моя статистика":
        s = user_stats[user_id]
        bot.send_message(
            chat_id,
            f"📊 *Твоя статистика*\n\n"
            f"🌟 Мотиваторов: {s['motiv_count']}\n"
            f"🎲 Фактов: {s['facts_shown']}\n"
            f"🏆 Достижений: {len(s['achievements'])}",
            parse_mode="Markdown"
        )

    elif text == "🏆 Достижения":
        if not user_stats[user_id]['achievements']:
            bot.send_message(chat_id, "🏆 Пока достижений нет.")
        else:
            txt = "🏆 *Твои достижения:*\n\n"
            for a in user_stats[user_id]['achievements']:
                txt += f"• {ACHIEVEMENTS[a]['name']}\n"
            bot.send_message(chat_id, txt, parse_mode="Markdown")

    else:
        bot.send_chat_action(chat_id, 'typing')
        bot.send_message(chat_id, get_ai_response(user_id, text))

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("✅ БОТ БРОСАЙ-КА 2.0 ЗАПУЩЕН (24/7)")
    bot.infinity_polling(skip_pending=True)
