from configparser import ConfigParser
import dotenv
import os
from ftx_client import FtxClient, instant_limit_order
import pandas as pd


class GridBot:
    ftx_client = None
    market_symbol = None
    sub_account = None

    def __init__(self, grid: pd.DataFrame):
        self.read_config()
        self.ftx_client_setup()

    def ftx_client_setup(self):
        # load .env
        dotenv.load_dotenv('.env')
        api_key = os.environ.get("API_FTX")
        secret_key = os.environ.get("SECRET_FTX")
        self.ftx_client = FtxClient(api_key,
                                    secret_key, self.sub_account)

    def read_config(self):
        config = ConfigParser()
        config.read('./public/config.ini')
        self.market_symbol = config['main']['market_symbol']
        self.sub_account = config["main"]['sub_account']


bot = GridBot()
print(bot.sub_account)
