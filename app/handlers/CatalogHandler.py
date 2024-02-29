from datetime import datetime
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

from app.database.models import ReferalLevel, Subscription

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
from app.utils.CrystalPayWrapper import CrystalPay
from app.utils.lolzapi import LolzteamApi
from app.utils.config import cf
from hashlib import md5

logger = getLogger(__name__)

SubData = CallbackData('sub','sub_id','action')

class Lolz(StatesGroup):
    lolz = State()
    lolz_check = State()

class Keyboard:
    @staticmethod
    def catalog(session:AutoClosebleSession):
        keyboard = InlineKeyboardMarkup(row_width=1)
        for sub in session.query(Subscription).all():
            keyboard.add(InlineKeyboardButton(f"{sub.name} | {sub.price}₽", callback_data=SubData.new(sub_id=sub.id,action='sub')))
        keyboard.add(InlineKeyboardButton('Назад', callback_data='back'))
        return keyboard
    
    @staticmethod
    def sub(session:AutoClosebleSession,sub:Subscription):
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton('Купить', callback_data=SubData.new(sub_id=sub.id,action='buy')))
        keyboard.add(InlineKeyboardButton('Назад', callback_data='back'))
        return keyboard

class CatalogHandler:
    def __init__(self,dp:Dispatcher):
        dp.register_callback_query_handler(self.catalog,text="sub",state='*')
        dp.register_callback_query_handler(self.sub,SubData.filter(action='sub'),state='*')
        dp.register_callback_query_handler(self.buy,SubData.filter(action='buy'),state='*')
        dp.register_callback_query_handler(self.crystal_pay_check,text_contains='catalog:crystal:pay:check:',state='*')
        dp.register_callback_query_handler(self.crystal_pay,text_contains='catalog_crystal_pay_',state='*')
        dp.register_callback_query_handler(self.lolz_team,text_contains='catalog_lolz_team_',state='*')
        dp.register_callback_query_handler(self.lolz_team_check,text_contains='catalog:lolz_team:pay:check:',state=Lolz.lolz)

    async def catalog(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        await call.message.edit_caption('Каталог',reply_markup=Keyboard.catalog(session))
        await state.reset_state()

    async def sub(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        sub_id = callback_data['sub_id']
        sub = session.query(Subscription).filter(Subscription.id == sub_id).first()
        await call.message.edit_caption(f"Подписка {sub.name} | {sub.price}₽ | Длительность {sub.duration.days} дней\n\n{sub.description}",reply_markup=Keyboard.sub(session,sub))
        await state.reset_state()

    async def buy(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,callback_data:dict):
        sub_id = callback_data['sub_id']
        sub = session.query(Subscription).filter(Subscription.id == sub_id).first()
        user = session.query(User).filter(User.id == call.from_user.id).first()
        if user.balance < sub.price:
            await call.message.edit_caption(f"Недостаточно средств")
            await self.buy_select_payment(call,state,session,sub.price,sub_id)
            return
        user.balance -= sub.price
        user.subscription = sub
        user.expire_at = datetime.now() + sub.duration
        if cf.refferal_system:
            lvl = session.query(ReferalLevel).filter(ReferalLevel.count <= len(user.refferals)).order_by(ReferalLevel.count.desc()).first() \
            or session.query(ReferalLevel).order_by(ReferalLevel.count.desc()).first()
            user.expire_at += lvl.bonus_time
        session.commit()
        if cf.refferal_system:
            await call.message.edit_caption(f"Подписка успешно куплена\n\n{sub.name} | {sub.price}₽ | Длительность {sub.duration.days} дней\n\nВам начислено {lvl.bonus_time.days} дней бонуса за рефералов",
                                        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data='back')))
        else:
            await call.message.edit_caption(f"Подписка успешно куплена\n\n{sub.name} | {sub.price}₽ | Длительность {sub.duration.days} дней",
                                        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data='back')))
        await state.reset_state()

    async def buy_select_payment(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession,price:int,sub_id:int):
        await call.message.edit_caption(
            'Выберите способ оплаты',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("Crystal pay",callback_data=f'catalog_crystal_pay_{sub_id}_{price}')).add(
                InlineKeyboardButton("Lolz team",callback_data=f'catalog_lolz_team_{sub_id}_{price}')).add(
                InlineKeyboardButton("Назад",callback_data='back')
        )
        )
        await state.reset_state()

    async def crystal_pay(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        crystal = CrystalPay(os.getenv('CRYSTAL_PAY_TOKEN'),os.getenv('CRYSTAL_PAY_SECRET'))
        price = call.data.split('_')[-1]
        sub_id = call.data.split('_')[-2]
        url = await crystal.create_invoice(price)
        await call.message.edit_caption(
            'Оплата через Crystal pay',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("Перейти к оплате",url=url.url)).add(
                InlineKeyboardButton("Проверить оплату",callback_data=f'catalog:crystal:pay:check:{sub_id}:{url.id}')).add(
                InlineKeyboardButton("Назад",callback_data='back')
        )
        )

    async def crystal_pay_check(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        crystal = CrystalPay(os.getenv('CRYSTAL_PAY_TOKEN'),os.getenv('CRYSTAL_PAY_SECRET'))
        invoice_id = call.data.split(':')[-1]
        invoice = crystal.construct_payment_by_id(invoice_id)
        if invoice.if_paid():
            user = session.query(User).filter(User.id == call.from_user.id).first()
            user.balance += invoice.amount
            session.commit()
            await self.buy(call,state,session,{"sub_id":call.data.split(':')[-2]})
        else:
            await call.answer('Оплата не найдена')

    async def lolz_team(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        api = LolzteamApi(os.getenv('LOLZ_TEAM_TOKEN'),os.getenv('LOLZ_TEAM_USER_ID'))
        price = call.data.split('_')[-1]
        sub_id = call.data.split('_')[-2]
        hash = md5(f'{call.from_user.id}{price}{sub_id}'.encode()).hexdigest()
        await call.message.edit_caption(
            f'Оплата через Lolz team\n\nПереведите {price} пользователю {os.getenv("LOLZ_TEAM_USER_LINK")}\nВ комментарии укажите {hash}',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("Проверить оплату",callback_data=f'catalog:lolz_team:pay:check:{sub_id}:{price}')).add(
                InlineKeyboardButton("Назад",callback_data='back')
        )
        )
        await Lolz.lolz.set()
        await state.update_data({'hash':hash})
    
    async def lolz_team_check(self,call:types.CallbackQuery,state:FSMContext,session:AutoClosebleSession):
        price = call.data.split(':')[-1]
        sub_id = call.data.split(':')[-2]
        hash = (await state.get_data())["hash"]
        user = session.query(User).filter(User.id == call.from_user.id).first()
        api = LolzteamApi(os.getenv('LOLZ_TEAM_TOKEN'),os.getenv('LOLZ_TEAM_USER_ID'))
        if api.market_payments(type_='income', pmin=price, pmax=price, comment=hash)['payments']:
            user.balance += price
            session.commit()
            await self.buy(call,state,session,{"sub_id":sub_id})
        else:
            await call.answer('Оплата не найдена')


            