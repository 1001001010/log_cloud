from datetime import datetime, timedelta
import io
import os
import random
from aiogram import types,Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text,Command,BoundFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils.exceptions import MessageNotModified, MessageToDeleteNotFound, MessageCantBeDeleted, MessageTextIsEmpty, MessageCantBeEdited

from app.database.models import ReferalLevel

from ..database import User,AutoClosebleSession
from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.utils.deep_linking import get_start_link, get_startgroup_link
from aiogram.utils.exceptions import MessageNotModified, MessageToDeleteNotFound, MessageCantBeDeleted, MessageTextIsEmpty, MessageCantBeEdited
from aiogram.utils.markdown import hbold, hcode, hitalic, hlink, hpre, hunderline, hstrikethrough
from aiogram.types import (InlineKeyboardMarkup, 
                        InlineKeyboardButton, 
                        ReplyKeyboardMarkup,
                        KeyboardButton,
                        ReplyKeyboardRemove, 
                        InputMediaPhoto, 
                        InputMediaVideo, 
                        InputMediaAnimation, 
                        InputMediaDocument, 
                        InputMediaAudio, 
                        InputMedia)

from app.utils import getLogger

logger = getLogger(__name__)


class Keyboard:

    @staticmethod
    def main_menu(user:User):
        keyboard = InlineKeyboardMarkup()
        if user.is_admin:
            keyboard.add(InlineKeyboardButton('👨‍💻 Админ панель',callback_data='admin_panel'))
        if not user.subscription:
            keyboard.add(InlineKeyboardButton('📤 Оформить подписку',callback_data='sub'))
        keyboard.add(InlineKeyboardButton('👤 Профиль',callback_data='profile'))
        keyboard.add(InlineKeyboardButton("📝 Правила",callback_data='rules'))
        keyboard.insert(InlineKeyboardButton("👨‍💻 Помощь",callback_data='help'))
        return keyboard
    
    @staticmethod
    def profile(user:User, stat:bool = False):
        keyboard = InlineKeyboardMarkup()
        if not stat:
            keyboard.add(InlineKeyboardButton('📊 Моя статистика',callback_data='my_stat'))
        else:
            keyboard.add(InlineKeyboardButton('👤 Профиль',callback_data='profile'))
        keyboard.add(InlineKeyboardButton('👥 Рефералы',callback_data='refferals'))
        keyboard.add(InlineKeyboardButton('🔙 Назад',callback_data='back'))
        return keyboard

    @staticmethod
    def refferal_menu(user:User):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton('🔙 Назад',callback_data='profile'))
        return keyboard

class MainHandler:

    def __init__(self,dp:Dispatcher):
        dp.register_message_handler(self.start,commands=['start'],state='*')
        dp.register_callback_query_handler(self.profile,text="profile",state='*')
        dp.register_callback_query_handler(self.main_menu,text="back",state='*')
        dp.register_callback_query_handler(self.my_stat,text="my_stat",state='*')
        dp.register_callback_query_handler(self.refferal_menu,text="refferals",state='*')
        dp.register_callback_query_handler(self.rules,text="rules",state='*')
        dp.register_callback_query_handler(self.support,text="help",state='*')

    async def start(self,message:types.Message,state:FSMContext,user:User,session:AutoClosebleSession):
        if user is None:
            user = User()
            user.id = message.from_user.id
            user.username = message.from_user.username
            if message.get_args():
                if (user_ := session.query(User).filter(User.id == int(message.get_args())).first()):
                    user.refferal_id = int(message.get_args())
                    user.refferal = user_
                    user_.refferals.append(user)
                    session.add(user_)
                    session.commit()
            session.add(user)
            session.commit()
        await message.answer_photo(photo=open(os.path.join(os.getcwd(),'app','static','main_menu.png'),"rb"),caption=f'Привет, {message.from_user.full_name}!\n\nТы попал в облоко логов',reply_markup=Keyboard.main_menu(user))
        await state.reset_state()
    
    async def main_menu(self,call:types.CallbackQuery,state:FSMContext,user:User,session:AutoClosebleSession):
        await call.message.edit_media(
            media=InputMediaPhoto(media=open(os.path.join(os.getcwd(),'app','static','main_menu.png'),"rb"),caption=f'Привет, {call.from_user.full_name}!\n\nТы попал в облоко логов'),
            reply_markup=Keyboard.main_menu(user)
        )

    async def profile(self,call:types.CallbackQuery,state:FSMContext,user:User,session:AutoClosebleSession):
        text = f'👤 Профиль\n\n' 
        text += f'🆔 ID: {user.id}\n'
        text += f'👨‍💻 Username: @{user.username}\n'
        text += f'📤 Подписка: {"Активна" if user.subscription else "Не активна"}\n'
        if user.subscription:
            text += f'📅 Дата окончания подписки: {user.expire_at.strftime("%d.%m.%Y")}\n'
        text += f'💰 Баланс: {user.balance} руб.\n'
        text += f'📅 Дата регистрации: {user.created_at.strftime("%d.%m.%Y")}\n\n'
        text += f'👨‍💻 Помощь: @logcloud_supportbot\n'
        bio = io.BytesIO()
        bio.name = 'profile.jpg'
        photos = await call.bot.get_user_profile_photos(user.id,limit=1)
        if photos.total_count:
            await photos.photos[0][-1].download(destination_file=bio)
            bio.seek(0)
            await call.message.edit_media(
                media=InputMediaPhoto(media=bio,caption=text),
                reply_markup=Keyboard.profile(user)
            )
        else:
            await call.message.edit_caption(caption=text,reply_markup=Keyboard.profile(user))

    async def my_stat(self,call:types.CallbackQuery,state:FSMContext,user:User,session:AutoClosebleSession):
        if user.subscription:

            template=f'📊 Моя статистика\n\n'\
                        f'📥 Всего логов: {len(user.subscription.logs)}\n'\
                        f'📥 Всего логов за сегодня: {len([log for log in user.subscription.logs if log.created_at.date() == datetime.now().date()])}\n'\
                        f'📥 Всего логов за неделю: {len([log for log in user.subscription.logs if log.created_at.date() >= (datetime.now() - timedelta(days=7)).date()])}\n'\
                        f'📥 Всего логов за месяц: {len([log for log in user.subscription.logs if log.created_at.date() >= (datetime.now() - timedelta(days=30)).date()])}\n'\
                        f'📥 Всего логов за год: {len([log for log in user.subscription.logs if log.created_at.date() >= (datetime.now() - timedelta(days=365)).date()])}\n'
            await call.message.edit_caption(caption=template,reply_markup=Keyboard.profile(user,stat=True))
        else:
            await call.message.edit_caption('У вас нет активной подписки',reply_markup=Keyboard.profile(user,stat=True))
                    
    async def refferal_menu(self,call:types.CallbackQuery,state:FSMContext,user:User,session:AutoClosebleSession):
        lvl = session.query(ReferalLevel).filter(ReferalLevel.count <= len(user.refferals)).order_by(ReferalLevel.count.desc()).first()\
              or session.query(ReferalLevel).order_by(ReferalLevel.count.desc()).first()
        
        await call.message.edit_caption(
            caption=f'👥 Реферальная программа\n\n'
                    f"👥 Количество рефералов: {len(user.refferals)}\n"
                    f"💰 Уровень: {lvl.lvl}\n"
                    f"💰 Бонус: {lvl.bonus_time}\n"
                    f'👨‍💻 Ваша реферальная ссылка: {await get_start_link(user.id)}\n',
            reply_markup=Keyboard.refferal_menu(user)
        )

    async def rules(self,call:types.CallbackQuery,state:FSMContext,user:User,session:AutoClosebleSession):
        await call.message.edit_caption(
            caption=f'📜 Правила\n\n'
                    f"{os.getenv('RULES')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text='На главную',callback_data='back')
                ]
            ])
        )

    async def support(self,call:types.CallbackQuery,state:FSMContext,user:User,session:AutoClosebleSession):
        await call.message.edit_caption(
            caption=f'👨‍💻 Поддержка\n\n'
                    f'👨‍💻 Помощь: {os.getenv("SUPPORT")}\n',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text='На главную',callback_data='back')
                ]
            ])
        )
