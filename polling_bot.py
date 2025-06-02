import json
import logging
import subprocess
import time
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters
from telegram.constants import ParseMode

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка API-ключей
with open('api_keys.json', 'r') as f:
    keys = json.load(f)

BOT_TOKEN = keys["bot_token"]
CHANNEL_USERNAME = f"@{keys['bot_username']}"  # или другое имя, если другой канал

# Глобальный флаг и задача анимации
edit_task = None
stop_animation = False

# Анимация статуса "создание группы"
async def animate_edit(bot: Bot, chat_id, message_id):
    global stop_animation
    dots = ["", ".", "..", "...", "..", "."]
    i = 0
    while not stop_animation:
        try:
            text = f"<i>Создание группы{dots[i % len(dots)]}</i>"
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            i += 1
            await asyncio.sleep(0.8)
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при обновлении статуса: {e}")
            break

async def handle_new_post(update: Update, context):
    global edit_task, stop_animation

    message = update.effective_message
    chat_id = message.chat_id
    message_id = message.message_id
    task_title = message.text.strip()

    logging.info(f"📬 Новый пост в канале: {task_title}")

    # Запускаем анимацию
    stop_animation = False
    edit_task = asyncio.create_task(animate_edit(context.bot, chat_id, message_id))

    # Запускаем create_group.py
    try:
        process = subprocess.run(
            [
                "python3", "create_group.py",
                "--group", task_title
            ],
            capture_output=True,
            text=True
        )
        output = process.stdout.strip()
        logging.info(f"✅ Скрипт выполнен:\n{output}")
    except Exception as e:
        logging.error(f"❌ Ошибка при выполнении скрипта: {e}")
        output = ""

    # Останавливаем анимацию
    stop_animation = True
    if edit_task:
        await edit_task

    # Ищем ссылку в выводе
    link = next((line for line in output.splitlines() if line.startswith("https://t.me/")), None)
    if link:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{task_title}\n\n🔗 <a href='{link}'>Чат по задаче</a>",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.warning(f"⚠️ Не удалось отредактировать сообщение: {e}")
    else:
        logging.warning("⚠️ Ссылка на группу не найдена в выводе скрипта.")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, handle_new_post))
    logging.info("🤖 Бот запущен. Ожидание новых постов...")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())