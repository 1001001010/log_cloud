import logging
import colorlog
import os 

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")



# Создание обработчика логгера, который выводит логи в стандартный поток вывода
handler = logging.StreamHandler()

# Создание форматировщика логов, который использует цвета
formatter = colorlog.ColoredFormatter(
    '%(green)s%(asctime)s%(reset)s | %(log_color)s%(levelname)-8s%(reset)s | %(blue)s%(name)s:%(funcName)s:%(lineno)d%(reset)s | %(log_color)s%(message)s %(reset)s',
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'white',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'white,bg_red',
    },
    secondary_log_colors={},
    style='%',
)

# Присваивание форматировщика обработчику логгера
handler.setFormatter(formatter)

class Log:
    def __init__(self) -> None:
        self.root_Log = self.getRootLogger()

    def getLogger(self, name):
        return self.root_Log.getChild(name)
    
    def getRootLogger(self):
        logger = logging.getLogger()
        logger.setLevel(LOG_LEVEL)
        logger.addHandler(handler)
        return logger
    

