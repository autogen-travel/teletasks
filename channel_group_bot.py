import logging
import asyncio
from configparser import ConfigParser
from telethon import TelegramClient, events
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest, GetParticipantRequest
from telethon.tl.functions.messages import ForwardMessagesRequest, EditMessageRequest
from telethon.tl.types import (ChannelParticipantsRecent, ChatAdminRights,
                                ChannelParticipantAdmin, ChannelParticipantCreator)
from telegram import Bot
from telegram.constants import ParseMode

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Загрузка конфигурации
config = ConfigParser()
config.read('config.ini')

API_ID = config.getint('telethon', 'api_id')
API_HASH = config.get('telethon', 'api_hash')
SESSION_NAME = config.get('telethon', 'session')
BOT_TOKEN = config.get('bot', 'token')

# Инициализация клиентов
bot = Bot(token=BOT_TOKEN)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def get_channel_participants(channel):
    participants = []
    async for user in client.iter_participants(channel, filter=ChannelParticipantsRecent):
        participants.append(user)
    return participants

@client.on(events.NewMessage(chats=None))
async def handler(event):
    if not event.is_channel or not event.message.message:
        return

    channel = await event.get_chat()
    message = event.message
    original_text = message.message
    author_id = message.from_id.user_id if message.from_id else None

    logging.info(f"📬 Новый пост в канале {channel.title}")

    # Временное обновление поста
    creating_note = "\n\n⏳ Идёт создание группы..."
    try:
        await bot.edit_message_text(chat_id=channel.id, message_id=message.id, text=original_text + creating_note)
    except Exception as e:
        logging.warning(f"Не удалось отредактировать пост: {e}")

    # Название новой группы
    snippet = original_text[:200].replace('\n', ' ')
    group_title = f"{channel.title} - {snippet}"

    # Создание группы
    result = await client(CreateChannelRequest(
        title=group_title,
        about="Группа для обсуждения поста",
        megagroup=True
    ))
    new_group = result.chats[0]
    logging.info(f"✅ Группа создана: {new_group.title}")

    # Добавление участников
    participants = await get_channel_participants(channel)
    user_ids = [p.id for p in participants if not p.bot]
    logging.info(f"👥 Добавляем {len(user_ids)} участников...")
    for i in range(0, len(user_ids), 10):
        try:
            await client(InviteToChannelRequest(new_group.id, user_ids[i:i + 10]))
        except Exception as e:
            logging.warning(f"Ошибка при добавлении участников: {e}")

    # Назначение автора поста админом
    if author_id:
        try:
            author = await client.get_entity(author_id)
            participant = await client(GetParticipantRequest(channel=channel, user_id=author.id))

            if isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                await client(EditAdminRequest(
                    channel=new_group,
                    user_id=author,
                    admin_rights=ChatAdminRights(
                        change_info=False,
                        post_messages=True,
                        edit_messages=True,
                        delete_messages=True,
                        ban_users=True,
                        invite_users=True,
                        pin_messages=True,
                        add_admins=False,
                        anonymous=False,
                        manage_call=True,
                        manage_topics=True
                    ),
                    rank="Автор поста"
                ))
                logging.info(f"🛡 Назначен админом: @{author.username if author.username else author.id}")
        except Exception as e:
            logging.warning(f"❌ Не удалось обработать автора поста: {e}")

    # Пересылка поста в группу
    try:
        await client(ForwardMessagesRequest(
            from_peer=channel,
            to_peer=new_group,
            id=[message.id],
            with_my_score=False
        ))
        logging.info("📩 Пост переслан в группу")
    except Exception as e:
        logging.error(f"Ошибка при пересылке: {e}")

    # Обновление оригинального поста с ссылкой
    group_link = f"https://t.me/c/{str(new_group.id)[4:]}/1"
    final_text = original_text + f"\n\n➡ Обсуждение: {group_link}"
    try:
        await bot.edit_message_text(chat_id=channel.id, message_id=message.id, text=final_text, parse_mode=ParseMode.HTML)
        logging.info("✏️ Пост обновлён с ссылкой на группу")
    except Exception as e:
        logging.warning(f"Не удалось обновить пост: {e}")

async def main():
    await client.start()
    logging.info("🤖 Бот запущен")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())