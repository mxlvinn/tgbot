from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging
import os
import json
import time

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константи
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # Замініть на ваш токен
VIDEO_LINKS = [
    'https://youtu.be/eOpnW0A9DJU',  # Замініть на ваші відео
    'https://youtu.be/6JRrP13RXEQ',
    'https://youtu.be/ttCdNXR18No',
    'https://youtu.be/nfr98JD80V0',
    'https://youtu.be/Z90-cYYyQK0'
]
THANK_YOU_MESSAGE = "Дякуємо за перегляд відео! Будь ласка, оцініть матеріал від 1 до 10."
FEEDBACK_BUTTON_TEXT = "Залишити відгук"

# Створення бота
bot = Bot(token=TOKEN)

# Завантаження та збереження даних користувачів
def load_user_data():
    if os.path.exists('user_data.json'):
        with open('user_data.json', 'r') as file:
            return json.load(file)
    return {}

def save_user_data(user_data):
    with open('user_data.json', 'w') as file:
        json.dump(user_data, file)

# Команда /start
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data = load_user_data()

    # Налаштування даних користувача
    if user_id not in user_data:
        user_data[user_id] = {
            'video_index': 0,
            'schedule_id': None
        }
        save_user_data(user_data)
        update.message.reply_text('Привіт! Я розпочну надсилання відео найближчим часом.')

        # Запуск надсилання відео через 10 секунд
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            send_next_video,
            'date',
            run_date=datetime.now() + timedelta(seconds=10),
            args=[user_id],
            id=f'user_{user_id}_video_send',
            name=f'Send video to user {user_id}',
            replace_existing=True
        )
        scheduler.start()
        logger.info(f'Scheduled video send for user {user_id}')

# Надсилання відео
def send_next_video(user_id):
    user_data = load_user_data()
    if user_id in user_data:
        video_index = user_data[user_id]['video_index']
        if video_index < len(VIDEO_LINKS):
            video_url = VIDEO_LINKS[video_index]
            bot.send_message(chat_id=user_id, text=f'Відео {video_index + 1} надіслано.')
            bot.send_message(chat_id=user_id, text=video_url)  # Надсилаємо URL відео

            # Оновлення індексу відео
            user_data[user_id]['video_index'] += 1
            save_user_data(user_data)

            # Планування надсилання наступного відео через 10 секунд
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                send_next_video,
                'date',
                run_date=datetime.now() + timedelta(seconds=10),
                args=[user_id],
                id=f'user_{user_id}_video_send',
                name=f'Send video to user {user_id}',
                replace_existing=True
            )
            scheduler.start()
        else:
            # Надсилання фінального повідомлення
            bot.send_message(
                chat_id=user_id,
                text=THANK_YOU_MESSAGE,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(FEEDBACK_BUTTON_TEXT, callback_data='feedback')]
                ])
            )
            logger.info(f'All videos sent to user {user_id}')

# Обробка зворотного зв'язку
def handle_feedback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    # Тут можна реалізувати функцію для збору зворотного зв'язку
    query.edit_message_text(text='Дякуємо за ваш відгук!')

def main():
    # Налаштування Updater та диспетчера
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    # Додавання обробників команд
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(handle_feedback, pattern='feedback'))

    # Запуск бота
    updater.start_polling()

    # Запуск бота до отримання сигналу на зупинку
    updater.idle()

if __name__ == '__main__':
    main()
