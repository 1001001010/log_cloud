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

from app.database.models import Log, ReferalLevel, Subscription

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
                        InputMedia,
                        InputFile)

from app.utils import getLogger
from matplotlib import pyplot as plt
import pytz
from app.utils.config import cf

logger = getLogger(__name__)

UserData = CallbackData('user','id','action')
LogData = CallbackData('log','id','action')
SubData = CallbackData('sub-admin','id','action')

class SubscriptionsState(StatesGroup):
    name = State()
    description = State()
    price = State()
    duration = State()

class AddSub(StatesGroup):
    subscription = State()
    until_date = State()

class LogState(StatesGroup):
    file = State()
    count = State()
    send_at = State()
    subscription = State()
    change_date = State()

class ReferralSystemState(StatesGroup):
    time = State()
    count = State()
class Keyboard:
    @staticmethod
    def admin_panel():
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton('📁 Логи',callback_data='admin_logs'))
        keyboard.add(InlineKeyboardButton('📊 Статистика',callback_data='admin_stat'))
        keyboard.insert(InlineKeyboardButton('👨 Пользователи',callback_data='admin_users'))
        keyboard.add(InlineKeyboardButton('🎟 Подписки',callback_data='admin_subscriptions'))
        keyboard.insert(InlineKeyboardButton('📬 Рассылка',callback_data='send_message'))
        keyboard.add(InlineKeyboardButton('⚙️ Настройки',callback_data='admin_settings'))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='back'))
        return keyboard

    @staticmethod
    def users(session:AutoClosebleSession,page:int=1):
        keyboard = InlineKeyboardMarkup()
        users = session.query(User).filter(User.is_admin == False).all()
        for user in users[(page-1)*10:page*10]:
            keyboard.add(InlineKeyboardButton(f"[{user.id}] @{user.username}",callback_data=UserData.new(user.id,'user')))
        total_pages = len(users)//10 if len(users)%10 == 0 else len(users)//10+1
        if page > 1:
            keyboard.add(InlineKeyboardButton('⬅️',callback_data=UserData.new(page-1,'page')))
            keyboard.insert(InlineKeyboardButton(f"{page}/{total_pages}",callback_data='page'))
        else:
            keyboard.add(InlineKeyboardButton(f"{page}/{total_pages}",callback_data='page'))
        if page < total_pages:
            keyboard.insert(InlineKeyboardButton('➡️',callback_data=UserData.new(page+1,'page')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel'))
        return keyboard
        
    @staticmethod
    def user(session:AutoClosebleSession,user_id:int):
        keyboard = InlineKeyboardMarkup()
        user = session.query(User).filter(User.id == user_id).first()
        if user.is_banned:
            keyboard.insert(InlineKeyboardButton('👨‍💻 Разбанить',callback_data=UserData.new(user_id,'ban')))
        else:
            keyboard.insert(InlineKeyboardButton('👨‍💻 Забанить',callback_data=UserData.new(user_id,'ban')))
        if user.subscription:
            keyboard.add(InlineKeyboardButton('👨‍💻 Удалить подписку',callback_data=UserData.new(user_id,'delete_sub')))
        else:
            keyboard.add(InlineKeyboardButton('👨‍💻 Добавить подписку',callback_data=UserData.new(user_id,'add_sub')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_users'))
        return keyboard

    @staticmethod
    def notify(session:AutoClosebleSession,user_id:int):
        keyboard = InlineKeyboardMarkup()
        keyboard.insert(InlineKeyboardButton('👨‍💻 Уведомить',callback_data=UserData.new(user_id,'notify')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data=UserData.new(user_id,'user')))
        return keyboard
    
    @staticmethod
    def add_subscription(session:AutoClosebleSession):
        keyboard = InlineKeyboardMarkup()
        subscriptions = session.query(Subscription).all()
        for subscription in subscriptions:
            keyboard.insert(InlineKeyboardButton(f"{subscription.name}",callback_data=f"add_sub_{subscription.id}"))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_users'))
        return keyboard

    @staticmethod
    def logs(session:AutoClosebleSession):
        keyboard = InlineKeyboardMarkup()
        logs = session.query(Log).filter(Log.is_sended == False).all()
        for log in logs:
            date = log.send_at.astimezone(pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y %H:%M:%S')
            keyboard.add(InlineKeyboardButton(f"{log.id} {date}",callback_data=LogData.new(log.id,'log')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Добавить',callback_data=LogData.new(0,'add_log')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel'))
        return keyboard
    
    @staticmethod
    def log(session:AutoClosebleSession,log_id:int):
        keyboard = InlineKeyboardMarkup()
        log = session.query(Log).filter(Log.id == log_id).first()
        keyboard.insert(InlineKeyboardButton('👨‍💻 Отправить',callback_data=LogData.new(log_id,'send')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Изменить дату',callback_data=LogData.new(log_id,'change_date')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Удалить',callback_data=LogData.new(log_id,'delete')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs'))
        return keyboard

    @staticmethod
    def select_subscriptions(session:AutoClosebleSession,data:dict):
        keyboard = InlineKeyboardMarkup()
        subscriptions = session.query(Subscription).all()
        for subscription in subscriptions:
            if subscription.id in data.get('subscriptions',[]):
                keyboard.insert(InlineKeyboardButton(f"{subscription.name} ✅",callback_data=f"sub_{subscription.id}"))
            else:
                keyboard.insert(InlineKeyboardButton(f"{subscription.name}",callback_data=f"sub_{subscription.id}"))
        keyboard.add(InlineKeyboardButton('👨‍💻 Готово',callback_data='admin_add_confirm'))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel'))
        return keyboard

    @staticmethod
    def settings(session:AutoClosebleSession):
        keyboard = InlineKeyboardMarkup()
        if cf.refferal_system:
            keyboard.insert(InlineKeyboardButton('👨‍💻 Реферальная система ✅',callback_data='admin_referral_system'))
        else:
            keyboard.insert(InlineKeyboardButton('👨‍💻 Реферальная система ❌',callback_data='admin_referral_system'))
        keyboard.add(InlineKeyboardButton('Уровни реферальной системы',callback_data='admin_referral_levels'))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel'))
        return keyboard
    
    @staticmethod
    def referral_system_lvls(session:AutoClosebleSession):
        keyboard = InlineKeyboardMarkup()
        levels = session.query(ReferalLevel).all()
        for level in levels:
            keyboard.add(InlineKeyboardButton(f"{level.lvl} уровень - {level.bonus_time}",callback_data=f"admin_referral_level_{level.id}"))
        keyboard.add(InlineKeyboardButton('👨‍💻 Добавить',callback_data='admin_referral_level_add'))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_settings'))
        return keyboard

    @staticmethod
    def subscriptions(session:AutoClosebleSession):
        keyboard = InlineKeyboardMarkup()
        subscriptions = session.query(Subscription).all()
        for subscription in subscriptions:
            keyboard.add(InlineKeyboardButton(f"{subscription.name}",callback_data=SubData.new(subscription.id,'sub')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Добавить',callback_data=SubData.new(0,'add_sub')))
        keyboard.add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel'))
        return keyboard

class AdminHandler:
    def __init__(self,dp:Dispatcher) -> None:
        dp.register_callback_query_handler(self.admin_panel,text='admin_panel',state='*')
        dp.register_callback_query_handler(self.admin_stat,text='admin_stat',state='*')
        dp.register_callback_query_handler(self.admin_users,text='admin_users',state='*')
        dp.register_callback_query_handler(self.admin_users_page,UserData.filter(action='page'),state='*')
        dp.register_callback_query_handler(self.admin_user,UserData.filter(action='user'),state='*')
        dp.register_callback_query_handler(self.admin_user_ban,UserData.filter(action='ban'),state='*')
        dp.register_callback_query_handler(self.admin_user_add_sub,UserData.filter(action='add_sub'),state='*')
        dp.register_callback_query_handler(self.admin_user_add_sub_handler,state=AddSub.subscription)
        dp.register_message_handler(self.admin_user_add_sub_until_date,state=AddSub.until_date)
        dp.register_callback_query_handler(self.admin_user_delete_sub,UserData.filter(action='delete_sub'),state='*')
        dp.register_callback_query_handler(self.admin_user_notify,UserData.filter(action='notify'),state='*')
        dp.register_callback_query_handler(self.admin_logs,text='admin_logs',state='*')
        dp.register_callback_query_handler(self.admin_log,LogData.filter(action='log'),state='*')
        dp.register_callback_query_handler(self.admin_log_send,LogData.filter(action='send'),state='*')
        dp.register_callback_query_handler(self.admin_log_delete,LogData.filter(action='delete'),state='*')
        dp.register_callback_query_handler(self.admin_log_change_date,LogData.filter(action='change_date'),state='*')
        dp.register_message_handler(self.admin_log_change_date_handler,state=LogState.change_date)
        dp.register_callback_query_handler(self.admin_add_log,LogData.filter(action='add_log'),state='*')
        dp.register_message_handler(self.admin_add_log_handler,state=LogState.file, content_types=['document'])
        dp.register_message_handler(self.admin_add_log_count_handler,state=LogState.count)
        dp.register_message_handler(self.admin_add_log_send_date_handler,state=LogState.send_at)
        dp.register_callback_query_handler(self.admin_add_log_confirm_handler,text='admin_add_confirm',state='*')
        dp.register_callback_query_handler(self.admin_add_log_subscription_handler,state=LogState.subscription)
        dp.register_callback_query_handler(self.admin_settings,text='admin_settings',state='*')
        dp.register_callback_query_handler(self.admin_referral_system,text='admin_referral_system',state='*')
        dp.register_callback_query_handler(self.admin_referral_system_lvls,text='admin_referral_levels',state='*')
        dp.register_callback_query_handler(self.admin_referral_system_lvl_add,text='admin_referral_level_add',state='*')
        dp.register_message_handler(self.admin_referral_system_lvl_add_handler,state=ReferralSystemState.time)
        dp.register_message_handler(self.admin_referral_system_lvl_add_handler_count,state=ReferralSystemState.count)
        dp.register_callback_query_handler(self.admin_referral_system_lvl,text_contains='admin_referral_level_',state='*')
        dp.register_callback_query_handler(self.subscriptions,text='admin_subscriptions',state='*')
        dp.register_callback_query_handler(self.subscriptions_add,SubData.filter(action='add_sub'),state='*')
        dp.register_message_handler(self.subscriptions_add_handler_name,state=SubscriptionsState.name)
        dp.register_message_handler(self.subscriptions_add_handler_price,state=SubscriptionsState.price)
        dp.register_message_handler(self.subscriptions_add_handler_duration,state=SubscriptionsState.duration)
        dp.register_message_handler(self.subscriptions_add_handler_description,state=SubscriptionsState.description)
        dp.register_callback_query_handler(self.subscriptions_delete,SubData.filter(action='sub'),state='*')


    async def admin_panel(self,call:types.CallbackQuery,state:FSMContext):
        await call.message.edit_media(InputMediaPhoto(open(os.path.join('app','static','main_menu.png'),'rb'),'Админ панель'),reply_markup=Keyboard.admin_panel())
        await state.reset_state()

    async def admin_stat(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        users = session.query(User).filter(User.is_admin == False).all()
        # Рисуем график статистики по пользователям
        plt.clf()
        plt.title('Статистика по пользователям')
        plt.xlabel('Пользователи')
        plt.ylabel('Количество')
        plt.bar(['Всего','С подпиской','Без подписки',"Забанены"],
                [len(users),
                len([user for user in users if user.subscription is not None]),
                len([user for user in users if user.subscription is None])
                ,len([user for user in users if user.is_banned])])
        bio = io.BytesIO()
        plt.savefig(bio,format='png')
        bio.seek(0)
        await call.message.edit_media(InputMediaPhoto(InputFile(bio),caption='Статистика по пользователям'),reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel')))
        await state.reset_state()
    
    async def admin_users(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        await call.message.edit_caption('Пользователи',reply_markup=Keyboard.users(session))
        await state.reset_state()

    async def admin_users_page(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        await call.message.edit_reply_markup(Keyboard.users(session,int(callback_data['id'])))
        await state.reset_state()

    async def admin_user(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        user = session.query(User).filter(User.id == callback_data['id']).first()
        await call.message.edit_caption(f"Пользователь [{user.id}] @{user.username}",reply_markup=Keyboard.user(session,user.id))
        await state.reset_state()

    async def admin_user_ban(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        user = session.query(User).filter(User.id == callback_data['id']).first()
        user.is_banned = not user.is_banned
        session.commit()
        await call.message.edit_caption(f"Пользователь [{user.id}] @{user.username}",reply_markup=Keyboard.user(session,user.id))
        await state.reset_state()

    async def admin_user_delete_sub(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        user = session.query(User).filter(User.id == callback_data['id']).first()
        user.subscription = None
        session.commit()
        await call.message.edit_caption(f"Пользователь [{user.id}] @{user.username}",reply_markup=Keyboard.notify(session,user.id))
        await state.reset_state()

    async def admin_user_notify(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        user = session.query(User).filter(User.id == callback_data['id']).first()
        try:
            await call.bot.send_message(user.id,'📢 Ваша подписка истекла, пожалуйста, продлите её')
        except:
            pass
        await call.message.edit_caption(f"Пользователь [{user.id}] @{user.username}",reply_markup=Keyboard.user(session,user.id))

        await state.reset_state()

    async def admin_user_add_sub(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        user = session.query(User).filter(User.id == callback_data['id']).first()
        message_ = await call.message.edit_caption("Выберите подписку",reply_markup=Keyboard.add_subscription(session))
        await AddSub.subscription.set()
        await state.update_data(user_id=user.id,message_id=message_.message_id)

    async def admin_user_add_sub_handler(self,callback_query:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        sub_id = int(callback_query.data.split('_')[-1])
        if session.query(Subscription).filter(Subscription.id == sub_id).first() is None:
            await callback_query.answer('Подписка не найдена')
            return
        await state.update_data(sub_id=sub_id)
        await callback_query.message.edit_caption('Введите дату окончания подписки в формате дд.мм.гггг',reply_markup=
        InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel')))
        await AddSub.until_date.set()
    
    async def admin_user_add_sub_until_date(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        try:
            until_date = datetime.strptime(message.text,'%d.%m.%Y')
            if until_date < datetime.now():
                raise Exception()
        except:
            data = await state.get_data()
            try:
                await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption='Неверный формат даты окончания подписки',reply_markup=
                InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_panel')))
            except:
                pass
            return
        data = await state.get_data()
        user = session.query(User).filter(User.id == data['user_id']).first()
        user.subscription_id = data['sub_id']
        user.expire_at = until_date 
        session.commit()
        await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption=f"Пользователь [{user.id}] @{user.username}\n\nПодписка до {until_date.strftime('%d.%m.%Y')} успешно добавлена",reply_markup=Keyboard.user(session,user.id))
        await state.reset_state()

    async def admin_logs(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        await call.message.edit_caption('Логи',reply_markup=Keyboard.logs(session))
        await state.reset_state()
    
    async def admin_log(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        log = session.query(Log).filter(Log.id == callback_data['id']).first()
        await call.message.edit_caption(f"Лог [{log.id}] {log.count}",reply_markup=Keyboard.log(session,log.id))
        await state.reset_state()

    async def admin_log_delete(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        log = session.query(Log).filter(Log.id == callback_data['id']).first()
        session.delete(log)
        session.commit()
        await call.message.edit_caption('Логи',reply_markup=Keyboard.logs(session))
        await state.reset_state()

    async def admin_log_send(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        log = session.query(Log).filter(Log.id == callback_data['id']).first()
        log.send_at = datetime.now()
        session.commit()
        await call.message.edit_caption(f"Логи",reply_markup=Keyboard.logs(session))
        await state.reset_state()

    async def admin_log_change_date(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        log = session.query(Log).filter(Log.id == callback_data['id']).first()
        message_ = await call.message.edit_caption(f"Лог [{log.id}] {log.count}\n\nВведите дату в формате дд.мм.гггг ч:м",reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))
        await LogState.change_date.set()
        await state.update_data(log_id=log.id,message_id=message_.message_id)
    
    async def admin_log_change_date_handler(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        try:
            date = datetime.strptime(message.text,'%d.%m.%Y %H:%M')
            moscow = pytz.timezone('Europe/Moscow')
            local = moscow.localize(date)
            date = local.astimezone(pytz.utc)
            if date.timestamp() < datetime.utcnow().timestamp():
                raise Exception()
        except:
            data = await state.get_data()
            try:
                await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption='Неверный формат даты',reply_markup=
                InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))
            except:
                pass
            return
        data = await state.get_data()
        log = session.query(Log).filter(Log.id == data['log_id']).first()
        log.send_at = date
        session.commit()
        await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption=f"Лог [{log.id}] {log.count}",reply_markup=Keyboard.log(session,log.id))
        await state.reset_state()

    async def admin_add_log(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        message_ = await call.message.edit_caption('Отправьте лог',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))
        await LogState.file.set()
        await state.update_data(message_id=message_.message_id)
    
    async def admin_add_log_handler(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        if message.document is None:
            
            try:
                await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption='Отправьте лог',reply_markup=
                InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))
            except:
                pass
            return
        await state.update_data(file_id=message.document.file_id)
        await LogState.count.set()
        await message.bot.edit_message_caption(message.chat.id, data['message_id']
                                               ,caption='Введите количество логов',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))

    async def admin_add_log_count_handler(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        if not message.text.isdigit():
            
            try:
                await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption='Введите количество логов',reply_markup=
                InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))
            except:
                pass
            return
        await state.update_data(count=int(message.text))
        await LogState.send_at.set()
        await message.bot.edit_message_caption(message.chat.id, data['message_id']
                                               ,caption='Введите дату в формате дд.мм.гггг ч:м',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))

    async def admin_add_log_send_date_handler(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        try:
            date = datetime.strptime(message.text,'%d.%m.%Y %H:%M')
            moscow = pytz.timezone('Europe/Moscow')
            local = moscow.localize(date)
            date = local.astimezone(pytz.utc)
            if date.timestamp() < datetime.utcnow().timestamp():
                raise Exception()
        except Exception as e:
            logger.error(e)
            
            try:
                await message.bot.edit_message_caption(message.chat.id,data['message_id'],caption='Неверный формат даты',reply_markup=
                InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_logs')))
            except:
                pass
            return
        await state.update_data(send_at=date)
        await LogState.subscription.set()
        await message.bot.edit_message_caption(message.chat.id,data["message_id"]
                                               ,caption='Выберите подписки',reply_markup=Keyboard.select_subscriptions(session,await state.get_data()))

    async def admin_add_log_subscription_handler(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        callback_data = {
            'id':int(call.data.split('_')[1]),
            'action':call.data.split('_')[0]
        }
        async with state.proxy() as data:
            if data.get('subscriptions') is None:
                data['subscriptions'] = []
            if callback_data['id'] in data['subscriptions']:
                data['subscriptions'].remove(callback_data['id'])
            else:
                data['subscriptions'].append(callback_data['id'])
        await call.message.edit_caption('Выберите подписки',reply_markup=Keyboard.select_subscriptions(session,data))

    async def admin_add_log_confirm_handler(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        data = await state.get_data()
        if data.get('subscriptions') is None:
            await call.message.edit_caption('Выберите подписки',reply_markup=Keyboard.select_subscriptions(session,data))
            return
        log = Log(data["file_id"],data["send_at"],data["count"])
        log.subscriptions.extend(session.query(Subscription).filter(Subscription.id.in_(data['subscriptions'])).all())
        session.add(log)
        session.commit()
        await call.message.edit_caption(f"Лог [{log.id}] {log.count}",reply_markup=Keyboard.log(session,log.id))
        await state.reset_state()

    async def admin_settings(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        await call.message.edit_caption('Настройки',reply_markup=Keyboard.settings(session))

    async def admin_referral_system(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        cf.refferal_system = not cf.refferal_system
        await call.message.edit_caption('Реферальная система включена' if cf.refferal_system else 'Реферальная система выключена',reply_markup=Keyboard.settings(session))

    async def admin_referral_system_lvls(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        await call.message.edit_caption('Нажмите чтобы удалить',reply_markup=Keyboard.referral_system_lvls(session))

    async def admin_referral_system_lvl(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        lvl = session.query(ReferalLevel).get(int(call.data.split('_')[-1]))
        session.delete(lvl)
        session.commit()
        await call.message.edit_caption('Нажмите чтобы удалить',reply_markup=Keyboard.referral_system_lvls(session))
    
    async def admin_referral_system_lvl_add(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        message_=await call.message.edit_caption('Введите количество реффералов',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_referral_system_lvls')))
        await ReferralSystemState.count.set()
        await state.update_data(message_id=message_.message_id)

    async def admin_referral_system_lvl_add_handler_count(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        if not message.text.isdigit():
            await message.bot.edit_message_caption(message.chat.id,data["message_id"]
                                                   ,caption='Неверный формат',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_referral_levels')))
            return
        await state.update_data(count=int(message.text))
        await ReferralSystemState.time.set()
        await message.bot.edit_message_caption(message.chat.id,data["message_id"]
                                                  ,caption='Введите доп время в формате дд.чч:мм:сс',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_referral_levels')))
        
    async def admin_referral_system_lvl_add_handler(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        if not message.text.count(':') == 2:
            await message.bot.edit_message_caption(message.chat.id,data["message_id"]
                                                   ,caption='Неверный формат',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_referral_levels')))
            return
        try:
            # Парсим интервал времени
            days = int(message.text.split('.')[0])
            message.text = message.text.split('.')[1]
            hours = int(message.text.split(':')[0])
            message.text = message.text.split(':')[1]
            minutes = int(message.text.split(':')[0])
            time = timedelta(
                days=days,hours=hours,minutes=minutes
            )

        except:
            await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Неверный формат',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='admin_referral_levels')))
            return
        ref = ReferalLevel()
        ref.name = "Уровень"
        ref.bonus_time = time
        ref.lvl = session.query(ReferalLevel).count() + 1
        ref.count = data["count"]
        session.add(ref)
        session.commit()
        await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Нажмите чтобы удалить',reply_markup=Keyboard.referral_system_lvls(session))
        await state.reset_state()

    async def subscriptions(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        await call.message.edit_caption('Нажмите чтобы удалить',reply_markup=Keyboard.subscriptions(session))

    async def subscriptions_add(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        message = await call.message.edit_caption('Введите название подписки',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='subscriptions')))
        await SubscriptionsState.name.set()
        await state.update_data(message_id=message.message_id)

    async def subscriptions_add_handler_name(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        await state.update_data(name=message.text)
        message = await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Введите описание подписки',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='subscriptions')))
        await SubscriptionsState.description.set()
        await state.update_data(message_id=message.message_id)
    
    async def subscriptions_add_handler_description(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        await state.update_data(description=message.text)
        message = await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Введите цену подписки',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='subscriptions')))
        await SubscriptionsState.price.set()
        await state.update_data(message_id=message.message_id)

    async def subscriptions_add_handler_price(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        if not message.text.isdigit():
            await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Неверный формат',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='subscriptions')))
            return
        await state.update_data(price=int(message.text))
        message = await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Введите количество дней подписки',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='subscriptions')))
        await SubscriptionsState.duration.set()
        await state.update_data(message_id=message.message_id)
    
    async def subscriptions_add_handler_duration(self,message:types.Message,state:FSMContext,session:AutoClosebleSession):
        await message.delete()
        data = await state.get_data()
        if not message.text.isdigit():
            await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Неверный формат',reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('👨‍💻 Назад',callback_data='subscriptions')))
            return
        sub = Subscription()
        sub.name = data["name"]
        sub.description = data["description"]
        sub.price = data["price"]
        sub.duration = timedelta(days=int(message.text))
        session.add(sub)
        session.commit()
        await message.bot.edit_message_caption(message.chat.id,data["message_id"],caption='Подписка добавлена',reply_markup=Keyboard.subscriptions(session))

    async def subscriptions_delete(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        id = callback_data["id"]
        session.query(Subscription).filter(Subscription.id == id).delete()
        session.commit()
        await call.message.edit_caption('Нажмите чтобы удалить',reply_markup=Keyboard.subscriptions(session))
    
























































































































