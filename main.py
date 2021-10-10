import json
import asyncio
from functools import partial
from telethon.sync import TelegramClient, events, Message, Button
from typing import Union
from functions import *
import os

API_ID = os.environ.get("API_ID", None)
API_HASH = os.environ.get("API_HASH", None)
TOKEN = os.environ.get("TOKEN", None)

bot = TelegramClient('bot', API_ID, API_HASH).start(
    bot_token=TOKEN)

permited_users = {}
users_list = {}
mimetypes = ('application/pdf', 'text/plain')


@bot.on(events.NewMessage(pattern='/get'))
async def get_users(event):
    chat_id = event.message.chat.id
    permited_users = {x.id: x.username for x in await bot.get_participants(chat_id, aggressive=True) if not x.bot}
    print(permited_users)
    with open('permitidos.json', 'w') as jsonfile:
        json.dump(permited_users, jsonfile, indent=4)
    await bot.send_message(chat_id, json.dumps(permited_users, indent=4))

NewMessage = Union[Message, events.NewMessage.Event]


def filter_type(message: NewMessage):
    if message.file:
        if message.media.document.mime_type in mimetypes:
            return True


@bot.on(events.NewMessage(func=filter_type))
async def get_files(event):
    message = event.message
    chat_id = message.chat.id
    mime_type = message.media.document.mime_type
    print(event)
    if chat_id in users_list.keys():
        if mime_type not in users_list[chat_id].keys():
            users_list[chat_id][mime_type] = []
        users_list[chat_id][mime_type].append(message.id)
    else:
        users_list[chat_id] = {}
        users_list[chat_id][mime_type] = [message.id]
    print(users_list)


@bot.on(events.NewMessage(pattern='/list'))
async def get_list(event):
    chat_id = event.message.chat.id

    if chat_id not in users_list:
        text_to_send = "Aún ningún archivo para combinar."
    elif not users_list[chat_id]:
        text_to_send = "Lista vacia."
    else:
        text_to_send = "Lista de archivos a combinar por tipo:\n"
        for mime_type in users_list[chat_id]:
            text_to_send += f'\n**{mime_type}**:\n'
            for message_id in users_list[chat_id][mime_type]:
                message = await bot.get_messages(chat_id, limit=1, ids=message_id)
                text_to_send += f'{message.media.document.attributes[0].file_name}\n'

    await event.reply(text_to_send)


@bot.on(events.NewMessage(pattern='/clear'))
async def clear_list(event):
    users_list[event.message.chat.id] = {}
    await event.reply('Lista limpiada')


@bot.on(events.NewMessage(pattern='/merge'))
async def merge(event):
    buttons = [Button.inline(x) for x in users_list[event.message.chat.id].keys()]
    await event.reply('Elija el tipo de archivo a combinar:', buttons=buttons)


@bot.on(events.CallbackQuery)
async def handler(event):
    chat_id = event.original_update.user_id
    async with bot.conversation(chat_id) as conv:
        message = (await conv.send_message('Diga el nombre del archivo:'))
        name_file_final = (await conv.get_response()).raw_text
        await message.delete()
        await conv.cancel_all()

    mime_type = event.data.decode('utf-8')
    dirpath = f'{chat_id}\{mime_type.replace("/", "-")}'

    for message_id in users_list[chat_id][mime_type]:
        message = await bot.get_messages(chat_id, limit=1, ids=message_id)
        await download_file(message, event, dirpath)

    await event.edit("Descargas finalizadas, procediendo a unir")

    if mime_type == 'application/pdf':
        name_file_final += '.pdf'
        merge_pdf(dirpath, name_file_final)

    elif mime_type == 'text/plain':
        name_file_final += '.txt'
        merge_txt(dirpath, name_file_final)

    file = f'{chat_id}\{name_file_final}'
    await bot.send_file(chat_id, file=file,
                        progress_callback=partial(
                            progress_handler, event, name_file_final, "Subiendo"))
    os.remove(file)
    await event.edit("Subido")
    users_list[chat_id][mime_type]=[]


async def download_file(message: Message, event: Message, dirpath: str):
    filename = message.media.document.attributes[0].file_name
    filepath = f'{dirpath}\{filename}'
    try:
        file = await message.download_media(file=filepath,
                                            progress_callback=partial(
                                                progress_handler, event, filename, "Descargando"))
        if file:
            await event.edit("Descarga exitosa")
    except Exception as exc:
        await message.edit(exc)


async def progress_handler(event: Message, filename: str, message_to_send: str, received_bytes, total_bytes):
    print(filename)
    try:
        await event.edit("{0} {1}\nProgreso: {2}%".format(message_to_send
                                                          , filename,
                                                          round(int(received_bytes) * 100 / int(total_bytes), 2))
                         )
    except asyncio.CancelledError as exc:
        raise exc
    except Exception as exc:
        print(exc)

if __name__ == "__main__":
    bot.run_until_disconnected()