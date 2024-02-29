from datetime import datetime, timedelta
import os
import random
from aiogram import types,Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text,Command,BoundFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils.exceptions import MessageNotModified, MessageToDeleteNotFound, MessageCantBeDeleted, MessageTextIsEmpty, MessageCantBeEdited
from ..database import Dal, User,AutoClosebleSession
from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.utils.deep_linking import get_start_link, get_startgroup_link
from aiogram.utils.exceptions import MessageNotModified, MessageToDeleteNotFound, MessageCantBeDeleted, MessageTextIsEmpty, MessageCantBeEdited
from aiogram.utils.markdown import hbold, hcode, hitalic, hlink, hpre, hunderline, hstrikethrough
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto,InputMediaAudio,InputMediaVideo,InputMediaDocument)
from app.utils import getLogger
import matplotlib
import matplotlib.pyplot as plt
import io


logger = getLogger(__name__)

class MailinStates(StatesGroup):
    text = State()
    documents = State()
    confirm = State()
    urls = State()

class Keyboard(Helper):
    @staticmethod
    def mailing(add_urls=False,add_files=False,close=False):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Отправить',callback_data='confirm'))
        if add_files:
            markup.add(InlineKeyboardButton('Добавить файлы',callback_data='add_files'))
        if add_urls:
            markup.add(InlineKeyboardButton('Добавить ссылку',callback_data='add_urls'))
        markup.add(InlineKeyboardButton('Отмена',callback_data='admin_panel'))
        return markup
        

class MailingHandler(StatesGroup):
    def __init__(self,dp:Dispatcher):
        dp.register_callback_query_handler(self.mailing,text="send_message",state='*')
        dp.register_callback_query_handler(self.add_files, text="add_files",state=MailinStates.confirm)
        dp.register_callback_query_handler(self.add_urls, text="add_urls",state=MailinStates.confirm)
        dp.register_callback_query_handler(self.back_mail, text="back_mail",state=MailinStates.confirm)
        dp.register_message_handler(self.text,state=MailinStates.text)
        dp.register_message_handler(self.documents,state=MailinStates.documents, content_types=['photo','video','audio','voice','document'])
        dp.register_message_handler(self.urls,state=MailinStates.urls)
        dp.register_callback_query_handler(self.confirm, text="confirm",state=MailinStates.confirm)
        

    async def mailing(self, call: types.CallbackQuery,state:FSMContext):
        await call.message.edit_caption('Введите текст рассылки',reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('Отмена',callback_data='amdin_panel')))
        await MailinStates.text.set()
        await state.update_data(message_id=call.message.message_id)

    async def text(self,message:types.Message,state:FSMContext):
        await message.delete()
        data = await state.get_data()
        message_id = data.get('message_id')
        await message.bot.edit_message_caption(message_id=message_id,chat_id=message.chat.id,caption='Текст рассылки:\n'+message.text,reply_markup=Keyboard.mailing(add_urls=True,add_files=True))
        await MailinStates.confirm.set()   
        await state.update_data(text=message.text)
        await state.update_data(closed=False)
    
    async def add_files(self,call: types.CallbackQuery,state:FSMContext):
        await call.message.edit_caption('Отправьте файлы',reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('Отмена',callback_data='back_mail')))
        await MailinStates.documents.set()
        
    async def documents(self,message:types.Message,state:FSMContext):
        files_id = {
            'photo':message.photo[-1].file_id if message.photo else None,
            'video':message.video.file_id if message.video else None,
            'audio':message.audio.file_id if message.audio else None,
            'voice':message.voice.file_id if message.voice else None,
            'document':message.document.file_id if message.document else None,
        }

        await message.delete()
        data = await state.get_data()
        message_id = data.get('message_id')
        async with state.proxy() as data:
            if data.get('documents') is None:
                data['documents'] = []
            data['documents'].append({'file_id':files_id[message.content_type],'type':message.content_type})
        if len(data['documents']) > 1:
            await message.bot.edit_message_caption(message_id=message_id,chat_id=message.chat.id,caption='Файлы добавлены',reply_markup=Keyboard.mailing(add_urls=False,add_files =len(data['documents']) < 10,close=data.get('closed')))
        else:
            await message.bot.edit_message_caption(message_id=message_id,chat_id=message.chat.id,caption='Файл добавлен',reply_markup=Keyboard.mailing(add_urls=True,add_files =len(data['documents']) < 10,close=data.get('closed')))
        await MailinStates.confirm.set()   
    
    async def add_urls(self,call: types.CallbackQuery,state:FSMContext):
        await call.message.edit_caption('Введите ссылку в виде "название кнопки:url"',reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('Отмена',callback_data='back_mail')))
        await MailinStates.urls.set()

    async def urls(self,message:types.Message,state:FSMContext):
        await message.delete()
        data = await state.get_data()
        message_id = data.get('message_id')
        async with state.proxy() as data:
            if data.get('urls') is None:
                data['urls'] = []
            data['urls'].append(message.text)
            if data.get("documents") is None:
                documents = []
            else:
                documents = data.get("documents")
        if len(data['urls']) > 1:
            await message.bot.edit_message_caption(message_id=message_id,chat_id=message.chat.id,caption='Ссылки добавлены',reply_markup=Keyboard.mailing(add_urls=len(data['urls']) < 10,add_files=len(documents) == 0,close=data.get('closed')))
        else:
            await message.bot.edit_message_caption(message_id=message_id,chat_id=message.chat.id,caption='Ссылка добавлена',reply_markup=Keyboard.mailing(add_urls=len(data['urls']) < 10,add_files=len(documents) == 0,close=data.get('closed')))
        await MailinStates.confirm.set()   
    
    async def back_mail(self,call: types.CallbackQuery,state:FSMContext):
        text = (await state.get_data()).get('text')
        await call.message.edit_caption(text,reply_markup=Keyboard.mailing(add_urls=True,add_files=True))
        await MailinStates.confirm.set()   
    
    async def close(self,call: types.CallbackQuery,state:FSMContext):
        async with state.proxy() as data:
            if data.get('closed') is None:
                data['closed'] = False
        if data.get('closed'):
            await call.message.edit_reply_markup(reply_markup=Keyboard.mailing(add_urls=True,add_files=True,close=False))
            await state.update_data(closed=False)
        else:
            await call.message.edit_reply_markup(reply_markup=Keyboard.mailing(add_urls=True,add_files=True,close=True))
            await state.update_data(closed=True)

    async def confirm(self,call: types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        data = await state.get_data()
        message_id = data.get('message_id')
        await call.message.edit_caption('Рассылка началась')
        
        async with state.proxy() as data:
            text = data.get('text')
            documents = data.get('documents')
            urls = data.get('urls')
        if documents is None:
            documents = []
        if urls is None:
            urls = []
        markup = InlineKeyboardMarkup()
        for url in urls:
            name,url = url.split(':')
            markup.add(InlineKeyboardButton(name,url=url))
        logger.info(f'Рассылка началась с текстом {text} и файлами {documents} и ссылками {urls}')
        active_users = 0
        not_active_users = 0
        for user in session.query(User).filter(User.id != call.from_user.id).all():
            try:
                if len(documents) == 0:
                    await call.message.bot.send_message(user.id,text,reply_markup=markup)
                if len(documents) > 1:
                    media_group = []
                    for i,document in enumerate(documents):
                        if document['type'] == 'photo':
                            if i == 0:
                                media_group.append(InputMediaPhoto(document['file_id'],caption=text))
                            media_group.append(InputMediaPhoto(document['file_id']))
                        elif document['type'] == 'video':
                            if i == 0:
                                media_group.append(InputMediaVideo(document['file_id'],caption=text))
                            media_group.append(InputMediaVideo(document['file_id']))
                        elif document['type'] == 'audio':
                            if i == 0:
                                media_group.append(InputMediaAudio(document['file_id'],caption=text))
                            media_group.append(InputMediaAudio(document['file_id']))
                        elif document['type'] == 'document':
                            if i == 0:
                                media_group.append(InputMediaDocument(document['file_id'],caption=text))
                            media_group.append(InputMediaDocument(document['file_id']))
                    await call.message.bot.send_media_group(user.id,media_group)
                else:
                    for document in documents:
                        if document['type'] == 'photo':
                            await call.message.bot.send_photo(user.id,document['file_id'],text,reply_markup=markup)
                        elif document['type'] == 'video':
                            await call.message.bot.send_video(user.id,document['file_id'],text,reply_markup=markup)
                        elif document['type'] == 'audio':
                            await call.message.bot.send_audio(user.id,document['file_id'],text,reply_markup=markup)
                        elif document['type'] == 'voice':
                            await call.message.bot.send_voice(user.id,document['file_id'],text,reply_markup=markup)
                        elif document['type'] == 'document':
                            await call.message.bot.send_document(user.id,document['file_id'],text,reply_markup=markup)
                active_users += 1
            except Exception as e:
                logger.debug(f'Ошибка при рассылке {e}')
                not_active_users += 1

            await call.message.edit_caption(f'Рассылка началась\nАктивных пользователей: {active_users}\nНеактивных пользователей: {not_active_users}')

        await call.message.bot.edit_message_caption(message_id=message_id,chat_id=call.message.chat.id,caption=f'Рассылка завершена\nАктивных пользователей: {active_users}\nНеактивных пользователей: {not_active_users}',reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('Назад',callback_data='admin_panel')))
        await state.finish()