import json
import logging
import asyncio
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Читаем токен из api_keys.json
with open('api_keys.json', 'r') as f:
    keys = json.load(f)
BOT_TOKEN = keys['bot_token']


async def animate_edit(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Анимация с циклом 'создание группы...'"""
    states = ["создание группы", "создание группы.", "создание группы..", "создание группы..."]
    for _ in range(3):
        for state in states:
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=state)
                await asyncio.sleep(0.7)
            except Exception as e:
                logging.warning(f"Ошибка при анимации: {e}")
                return


async def handle_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not message.text:
        logging.info("Пост без текста, пропускаем")
        return

    post_text = message.text.strip()
    chat_id = message.chat.id
    message_id = message.message_id
    author_username = (message.from_user.username if message.from_user and message.from_user.username else "")

    logging.info(f"📬 Новый пост в канале: {post_text}")

    animation_task = asyncio.create_task(animate_edit(context, chat_id, message_id))

    try:
        process = await asyncio.create_subprocess_exec(
            'python3', 'create_group.py',
            '--group', post_text,
            '--author', author_username,
            '--first-post', post_text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        animation_task.cancel()

        if process.returncode != 0:
            logging.error(f"create_group.py ошибка:\n{stderr.decode()}")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=post_text)
            return

        output = stdout.decode()
        logging.info(f"✅ Скрипт выполнен:\n{output}")

        import re
        link_match = re.search(r'(https?://t\.me/[\w\+\-]+)', output)
        if not link_match:
            logging.warning("⚠️ Ссылка на группу не найдена.")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=post_text)
            return

        invite_link = link_match.group(1)
        new_text = f"{post_text}\n\n👉 [Ссылка на группу]({invite_link})"
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode="Markdown")

    except asyncio.CancelledError:
        logging.info("Анимация отменена.")
    except Exception as e:
        logging.error(f"Ошибка при создании группы: {e}")
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=post_text)


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    post_filter = filters.UpdateType.CHANNEL_POST & filters.TEXT
    application.add_handler(MessageHandler(post_filter, handle_new_post))
    logging.info("🤖 Бот запущен. Ожидание новых постов...")
    application.run_polling()