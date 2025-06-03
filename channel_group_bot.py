import asyncio
import logging
import json
import re

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest, GetParticipantsRequest
from telethon.tl.functions.messages import ExportChatInviteRequest, ForwardMessagesRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.types import ChatAdminRights, ChannelParticipantsRecent

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Загрузка конфигурации
with open('api_keys.json') as f:
    config = json.load(f)

api_id = config['api_id']
api_hash = config['api_hash']
bot_token = config['bot_token']
session_name = config['session_name']

# Инициализация Telethon клиента
client = TelegramClient(session_name, api_id, api_hash)


async def animate_edit(bot, chat_id, message_id):
    states = ["\n\u231b \u0418\u0434\u0451\u0442 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u0433\u0440\u0443\u043f\u043f\u044b" + "." * i for i in range(4)]
    for _ in range(5):
        for text in states:
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, disable_web_page_preview=True)
                await asyncio.sleep(0.6)
            except:
                return


async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not message.text:
        return

    post_text = message.text.strip()
    channel_id = message.chat.id
    message_id = message.message_id

    # Запускаем анимацию
    animation_task = asyncio.create_task(animate_edit(context.bot, channel_id, message_id))

    try:
        await client.start()

        # Получение объекта канала по ID
        channel_entity = await client.get_entity(channel_id)
        channel_title = channel_entity.title
        group_title = f"{channel_title} - {post_text[:200]}"

        # Получение автора поста
        full_message = await client.get_messages(channel_entity, ids=message_id)
        sender = await full_message.get_sender()
        sender_id = sender.id

        # Получение подписчиков канала
        participants = await client(GetParticipantsRequest(
            channel=channel_entity,
            filter=ChannelParticipantsRecent(),
            offset=0,
            limit=100,
            hash=0
        ))
        users_to_add = [p.participant.user_id for p in participants.users if p.id != sender_id]

        # Создание супергруппы
        result = await client(CreateChannelRequest(
            title=group_title,
            about="Группа, связанная с постом",
            megagroup=True
        ))
        group = result.chats[0]

        # Добавление пользователей
        for uid in users_to_add:
            try:
                await client(InviteToChannelRequest(channel=group, users=[uid]))
                await asyncio.sleep(1)
            except:
                logging.warning(f"Не удалось добавить участника {uid}")

        # Назначение автора поста админом
        try:
            rights = ChatAdminRights(
                change_info=False, post_messages=True, edit_messages=True, delete_messages=True,
                ban_users=True, invite_users=True, pin_messages=True, add_admins=False,
                manage_call=True, anonymous=False, manage_topics=True
            )
            await client(EditAdminRequest(channel=group, user_id=sender_id, admin_rights=rights, rank="Автор"))
        except Exception as e:
            logging.warning(f"Не удалось назначить админом: {e}")

        # Пересылка поста
        await client(ForwardMessagesRequest(
            from_peer=channel_entity,
            to_peer=group,
            id=[message_id],
            with_my_score=False
        ))

        # Ссылка на группу
        invite = await client(ExportChatInviteRequest(group))
        invite_link = invite.link

        # Обновление поста с ссылкой
        new_text = f"{post_text}\n\n\ud83d\udc49 [\u0421\u0441\u044b\u043b\u043a\u0430 \u043d\u0430 \u0433\u0440\u0443\u043f\u043f\u0443]({invite_link})"
        await context.bot.edit_message_text(chat_id=channel_id, message_id=message_id, text=new_text, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await context.bot.edit_message_text(chat_id=channel_id, message_id=message_id, text=post_text)
    finally:
        animation_task.cancel()
        await client.disconnect()


if __name__ == '__main__':
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.TEXT, handle_post))
    logging.info("\ud83e\udd16 Бот запущен")
    app.run_polling()
