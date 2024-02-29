import json
import os
from dotenv import load_dotenv

class Config:
    refferal_system = False


    def __write_config(self):
        with open("config.json", "w") as f:
            f.write(json.dumps(self.json(), indent=4))
    
    def __read_config(self):
        with open("config.json", "r") as f:
            data = json.loads(f.read())
            self.refferal_system = data["refferal_system"]

    def json(self):
        return {
            "refferal_system": self.refferal_system
        }
    
    @staticmethod
    def parse_row(row):
        return Config(
            refferal_system=row["refferal_system"]
        )
    
    def refresh(self):
        self.__read_config()
        return self

    def flush(self):
        self.__write_config()
        return self
    
cf = Config().refresh()
