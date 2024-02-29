from time import sleep
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as Ses, scoped_session
from app.utils import getLogger
import os
from dotenv import load_dotenv

load_dotenv()
logger = getLogger(__name__)


class AutoClosebleSession(Ses):
    def __del__(self):
        self.close()
    
    


class DataAccessLayer:
    def __init__(self, db_url: str, base, pool_recycle: int = 3600, pool_size: int = 5, max_overflow: int = 10, echo: bool = False,use_dev = False):
        self.db_url = db_url
        self.base = base
        self.pool_recycle = pool_recycle
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.echo = echo
        self.engine = None
        self.session = None
        self.Session = None
        self.use_dev = use_dev
        


    def connect(self) -> bool:
        """Connect to database.
        :return: True if connection was successful, False otherwise.
        """
        try:
            self.engine = create_engine(self.db_url, pool_recycle=self.pool_recycle, pool_size=self.pool_size,
                                        max_overflow=self.max_overflow, echo=self.echo)
            self.Session = sessionmaker(bind=self.engine, class_=AutoClosebleSession)
            if self.use_dev:
                logger.warning("Dropping all tables. Use only in development.")
                self.base.metadata.drop_all(self.engine)
            logger.debug("Creating all tables.")
            try:
                self.base.metadata.create_all(self.engine)
            except Exception as e:
                logger.error("Exception occured while creating tables.")
                logger.error(e)
                logger.error("Trying to create only missing tables.")
                sleep(5)
                try:
                    self.base.metadata.create_all(self.engine, checkfirst=True)
                except Exception as e:
                    exit(1)
                
            logger.debug("Connected to database. from url: " + self.db_url)
            return True
        except Exception as e:
            logger.error("Exception occured while connecting to database.")
            logger.error(e)
            return False
    
    
    def __enter__(self) -> AutoClosebleSession:
        """Enter the runtime context related to this object."""
        if self.engine is None:
            self.connect()
        if self.session is not None:
            #logger.warning("Session already exists. Closing it.")
            self.session.close()
        self.session = self.Session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context related to this object."""
        if exc_type is not None:
            logger.error("Exception occured in session. Rolling back.")
            logger.error("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
        self.session = None

    def __del__(self):
        if self.session is not None:
            #logger.warning("Session exists. Closing it.")
            self.session.close()
        if self.engine is not None:
            self.engine.dispose()
    
    
    def __call__(self) -> AutoClosebleSession:
        if self.engine is None:
            self.connect()
        if self.session is not None:
            self.session.close()
        self.session = self.Session()
        return self.session

        

        
    
        

    

    
