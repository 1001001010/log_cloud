import asyncio
import datetime
import logging
from aiogram import executor,Dispatcher,types
from app.handlers import MainHandler,AdminHandler,MailingHandler,CatalogHandler
from app import dp
import os
from .database import User,Dal,Subscription,Log
from app.utils import getLogger

logger = getLogger('bot')


async def background():
    logger.info('Запуск фоновых задач')
    while True:
        logger.debug('Проверка подписок')
        session = Dal()
        for user in session.query(User).filter(User.expire_at <= datetime.datetime.now()).all():
            user.expire_at = None
            user.subscription = None
            session.commit()
            try:
                await dp.bot.send_message(user.id, 'Ваша подписка истекла')
            except:
                pass
        session.close()
        logger.debug('Проверка подписок завершена Ожидание 5 секунд')
        await asyncio.sleep(5)
        logger.debug('Проверка логов')
        session = Dal()
        for log in session.query(Log).filter(Log.send_at <= datetime.datetime.now(),Log.is_sended == False).all():
            count_users = len([[user for user in sub.users] for sub in log.subscriptions])
            for sub in log.subscriptions:
                for user in sub.users:
                    try:
                        await dp.bot.send_document(user.id, log.file_id,caption=f"Количество логов {log.count}\n\nПолучили {count_users} человек")
                    except:
                        pass
            log.is_sended = True
            session.commit()
        session.close()
        logger.debug('Проверка логов завершена Ожидание 5 секунд')
        await asyncio.sleep(5)


async def on_startup(dp:Dispatcher):
    MainHandler(dp)
    CatalogHandler(dp) 
    AdminHandler(dp)
    MailingHandler(dp)
    
    dp['logger'] = getLogger('bot')
    
    asyncio.get_event_loop().create_task(background())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    