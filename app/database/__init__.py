from .models import *
from .core import DataAccessLayer,AutoClosebleSession
from dotenv import load_dotenv
import os
from app.utils import getLogger

logger = getLogger(__name__)

load_dotenv()

Dal = DataAccessLayer(
    db_url=os.getenv('DATABASE_URL'),
    base=Base,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=False,
    use_dev=False
)
if not Dal.connect():
    logger.error("Failed to connect to database. Exiting.")
    exit(1)

with Dal as session:
    if session.query(ReferalLevel).first() is None:
        lvl = ReferalLevel()
        lvl.lvl = 1
        lvl.name = "Первый уровень"
        lvl.bonus_time = timedelta(days=0,hours=0,minutes=0,seconds=0)

        session.add(lvl)
        session.commit()
        logger.info("Created default referal level")
    
    if session.query(User).filter(User.id == 944650271).first() is None:
        user = User()
        user.id = 944650271
        user.username = 'Kotik'
        user.is_admin = True
        session.add(user)
        session.commit()
        logger.info("Created default admin user")
        user = User()
        user.id = 5640543343
        user.username = 'M'
        user.is_admin = True
        session.add(user)
        session.commit()
        logger.info("Created default admin user")
