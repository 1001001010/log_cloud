from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from app.middlewares.DataAccessMiddleware import DataAccessMiddleware

load_dotenv()


bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(DataAccessMiddleware())
