import logging
import os
import json
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    JobQueue
)

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TOKEN = 'YOUR_BOT_TOKEN'
VIDEO_LINKS = [
    'https://youtu.be/eOpnW0A9DJU',
    'https://youtu.be/6JRrP13RXEQ',
    'https://youtu.be/ttCdNXR18No',
    'https://youtu.be/nfr98JD80V0',
    'https://youtu.be/Z90-cYYyQK0'
]
THANK_YOU_MESSAGE = "Дякуємо за перегляд відео! Будь ласка, оцініть матеріал від 1 до 10."
FEEDBACK_BUTTON_TEXT = "Залишити відгук"

# Bot initialization
application = Application.builder().token(TOKEN).build()


async def set_bot_commands(application):
    commands = [
        BotCommand(command="start", description="Розпочати або продовжити надсилання відео"),
        BotCommand(command="pause", description="Призупинити надсилання відео"),
        BotCommand(command="resume", description="Відновити надсилання відео"),
    ]
    await application.bot.set_my_commands(commands)


# Load and save user data functions
def load_user_data():
    logger.info("Loading user data from file.")
    if os.path.exists('user_data.json'):
        with open('user_data.json', 'r') as file:
            data = json.load(file)
            logger.info(f"User data loaded: {data}")
            return data
    logger.info("No user data file found, returning empty dictionary.")
    return {}


def save_user_data(user_data):
    logger.info(f"Saving user data to file: {user_data}")
    with open('user_data.json', 'w') as file:
        json.dump(user_data, file)
        logger.info("User data saved successfully.")


# Function to send the next video
async def send_next_video(context):
    job = context.job
    user_id = job.chat_id
    user_data = load_user_data()

    logger.info(f"Current user data: {user_data}")

    if str(user_id) in user_data:  # Ensure user_id is a string when accessing user_data
        video_index = user_data[str(user_id)]['video_index']
        logger.info(f"User {user_id} is at video index {video_index}.")

        if not user_data[str(user_id)].get('paused', False):  # Check if not paused
            if video_index < len(VIDEO_LINKS):
                # Attempt to send a video
                video_url = VIDEO_LINKS[video_index]
                logger.info(f"Attempting to send video {video_index + 1} to user {user_id}: {video_url}")

                try:
                    # Send the video message
                    response_video_1 = await context.bot.send_message(chat_id=user_id,
                                                                      text=f'Відео {video_index + 1} надіслано.')
                    response_video_2 = await context.bot.send_message(chat_id=user_id, text=video_url)
                    logger.info(
                        f"Video {video_index + 1} sent to user {user_id}. Responses: {response_video_1}, {response_video_2}")
                except Exception as e:
                    logger.error(f"Failed to send video to user {user_id}: {e}")

                # Update video index
                user_data[str(user_id)]['video_index'] += 1
                save_user_data(user_data)
            else:
                logger.info(f"All videos have been sent to user {user_id}. Ending job.")
                job.schedule_removal()
                try:
                    rating_buttons = [
                        [InlineKeyboardButton(str(i), callback_data=f"rating_{i}") for i in range(1, 6)],
                        [InlineKeyboardButton(str(i), callback_data=f"rating_{i}") for i in range(6, 11)]
                    ]

                    response_thank_you = await context.bot.send_message(
                        chat_id=user_id,
                        text=THANK_YOU_MESSAGE,
                        reply_markup=InlineKeyboardMarkup(rating_buttons)
                    )
                    logger.info(f"Thank you message sent to user {user_id}. Response: {response_thank_you}")
                except Exception as e:
                    logger.error(f"Failed to send thank you message to user {user_id}: {e}")
        else:
            logger.info(f"User {user_id} has paused the video sending.")
    else:
        logger.error(f"User ID {user_id} not found in user data.")


# Function to start the recurring video sending job
def start_video_sending(job_queue: JobQueue, user_id: int):
    job_queue.run_repeating(send_next_video, interval=timedelta(seconds=10), first=0, chat_id=user_id)


# Command handler for /start
async def start(update: Update, context):
    try:
        user_id = update.effective_user.id
        user_data = load_user_data()

        logger.info(f"Received /start command from user {user_id}")

        if str(user_id) not in user_data:
            user_data[str(user_id)] = {'video_index': 0, 'paused': False}
            save_user_data(user_data)

            # Send a preview message to introduce the bot
            intro_message = (
                "Привіт! Я бот, який надсилає вам корисні відео.\n\n"
                "Щоб розпочати, я надішлю вам кілька відео для перегляду. "
                "Після кожного відео ви зможете залишити свою оцінку.\n\n"
                "Доступні команди:\n"
                "/start - Розпочати або продовжити надсилання відео\n"
                "/pause - Призупинити надсилання відео\n"
                "/resume - Відновити надсилання відео"
            )
            await update.message.reply_text(intro_message)

            # Start the recurring video sending job
            start_video_sending(context.job_queue, user_id)
            logger.info(f"Started video sending for user {user_id}")
        else:
            await update.message.reply_text(
                "Ви вже зареєстровані в системі. Продовжую надсилати відео."
            )
            # If the user already exists, just continue sending videos
            start_video_sending(context.job_queue, user_id)

    except Exception as e:
        logger.error(f"Error in /start handler: {e}")


# Callback handler for rating buttons
async def handle_rating(update: Update, context):
    query = update.callback_query
    user_id = query.message.chat_id
    rating = int(query.data.split('_')[1])

    # Save the rating in the user data
    user_data = load_user_data()
    user_data[str(user_id)]['rating'] = rating
    save_user_data(user_data)

    await query.answer()  # Acknowledge the callback
    await query.edit_message_text(text=f"Дякуємо за вашу оцінку: {rating}!")


# Add handlers to the application
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_rating, pattern="rating_"))


# Main function to start the bot
def main():
    application.run_polling()


if __name__ == "__main__":
    main()
