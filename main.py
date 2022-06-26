from modules.ftx_client import FtxClient, instant_limit_order
from modules.log import add_row
from modules.tech import check_ta
from configparser import ConfigParser
import pandas as pd
import dotenv
import os
import time
import math
import datetime
import sys


class Bot:
    def __init__(self, grid_csv_path: str, conf_path: str, env_path: str = "./.env"):
        # config
        self.conf_path = conf_path
        self.env_path = env_path
        self.read_config()
        # ftx client setup
        self.ftx_client_setup()
        # grid setup
        self.grid = pd.read_csv(grid_csv_path, sep=',', index_col=0)
        self.grid_trading = self.grid.query(
            'price >= {} & price <= {}'.format(self.init_min_zone, self.init_max_zone))
        self.grid_trading.index = self.grid_trading.index - \
            self.grid_trading.index[0]
        # variables
        self.base_symbol = self.market_symbol.split('/')[0]
        self.quote_symbol = self.market_symbol.split('/')[1]
        # calculate init nav
        self.base_symbol_balance = self.ftx_client.get_balance_specific(
            self.base_symbol)
        self.quote_symbol_balance = self.ftx_client.get_balance_specific(
            self.quote_symbol)
        self.init_nav = float(0 if not self.base_symbol_balance else self.base_symbol_balance['usdValue']) + float(
            0 if not self.quote_symbol_balance else self.quote_symbol_balance['usdValue'])
        # check stablecoin balance amount
        self.grid_trading_posval_sum = self.grid_trading['value'].sum()
        if self.check_funds and (float(0 if not self.quote_symbol_balance else self.quote_symbol_balance['usdValue']) < self.grid_trading_posval_sum):
            raise Exception("Insufficient funds!")
        # check trailing_up mode
        if self.trailing_up and self.grid.iloc[0, 1] != self.grid.iloc[-1, 1]:
            raise Exception(
                "Trailing mode can only be used with fix position value.")
        # first update stats
        self.update_stats()

    def ftx_client_setup(self):
        dotenv.load_dotenv(self.env_path)
        api_key = os.environ.get("API_FTX")
        secret_key = os.environ.get("SECRET_FTX")
        self.ftx_client = FtxClient(api_key,
                                    secret_key, self.sub_account)

    def read_config(self):
        config = ConfigParser()
        config.read(self.conf_path)
        # main
        self.market_symbol = config['main']['market_symbol']
        self.sub_account = config["main"]['sub_account']
        self.check_funds = int(config["main"]['check_funds'])
        # technical analysis
        self.timeframe_buy = config["ta"]['timeframe_buy']
        self.ema1_len_buy = int(config["ta"]['ema1_len_buy'])
        self.ema2_len_buy = int(config["ta"]['ema2_len_buy'])
        self.timeframe_sell = config["ta"]['timeframe_sell']
        self.ema1_len_sell = int(config["ta"]['ema1_len_sell'])
        self.ema2_len_sell = int(config["ta"]['ema2_len_sell'])
        # grid
        self.trailing_up = int(config["grid"]['trailing_up'])
        self.init_max_zone = float(config["grid"]['init_max_zone'])
        self.init_min_zone = float(config["grid"]['init_min_zone'])
        self.stop_loss = float(config["grid"]['stop_loss'])

    def update_stats(self):
        # check exhange pair and price
        self.market_info = self.ftx_client.get_single_market(
            self.market_symbol)
        if self.market_info['enabled'] == False:
            raise Exception("FTX suspended trading!")
        self.price = self.market_info['price']
        # calculate nav
        self.base_symbol_balance = self.ftx_client.get_balance_specific(
            self.base_symbol)
        self.quote_symbol_balance = self.ftx_client.get_balance_specific(
            self.quote_symbol)
        self.nav = float(0 if not self.base_symbol_balance else self.base_symbol_balance['usdValue']) + float(
            0 if not self.quote_symbol_balance else self.quote_symbol_balance['usdValue'])
        self.nav_pct = self.nav/self.init_nav*100
        # avg buy price
        self.avg_buy_price = round((self.init_nav - float(0 if not self.quote_symbol_balance else self.quote_symbol_balance['free']))/float(
            -1 if not self.base_symbol_balance or self.base_symbol_balance['free'] == 0 else self.base_symbol_balance['free']), 2)

    def display_stats(self):
        #os.system('cls' if os.name == 'nt' else 'clear')
        print("--------------------")
        print("[CONFIG]")
        print("market_symbol:", self.market_symbol)
        print("sub_account:", self.sub_account)
        print("grid_zone_all:", round(
            self.grid.iloc[-1, 0], 2), "=>", self.grid.iloc[0, 0])
        print("grid_trading_posval_sum:", round(
            self.grid_trading_posval_sum, 2))
        print("-------------------")
        print("[STATUS]")
        print("{}: {}".format(self.market_symbol, self.price))
        print(self.base_symbol+" balance: " +
              str(round(float(0 if not self.base_symbol_balance else self.base_symbol_balance['free']), 4)))
        print(self.quote_symbol+" balance: " +
              str(round(float(0 if not self.quote_symbol_balance else self.quote_symbol_balance['free']), 2)))
        print("NAV: "+str(round(self.nav, 2))+"/" +
              str(round(self.init_nav, 2))+" ["+str(int(self.nav_pct))+"%]")
        print("grid_zone_trading:", round(
            self.grid_trading.iloc[-1, 0], 2), "=>", self.grid_trading.iloc[0, 0])
        print("avg_buy_price:", self.avg_buy_price)
        print("--------------------")

    def run(self):
        while True:
            try:
                # price tick
                self.update_stats()
                # update config
                self.read_config()

                # check trailing up
                if self.trailing_up:
                    # trail up
                    if self.price > self.grid_trading.iloc[0, 0] and self.price < self.grid.iloc[0, 0]:
                        self.grid_trading = self.grid_trading.iloc[0:-1]
                        new_grid = []
                        grid_upper_zone = self.grid.query(
                            'price > {}'.format(self.grid_trading.iloc[0, 0]))
                        for i in range(len(grid_upper_zone.index)-1, -1, -1):
                            if grid_upper_zone.iloc[i, 0] < self.price:
                                new_grid.append(
                                    grid_upper_zone.iloc[i].to_list())
                        if len(new_grid) > 0:
                            for g in new_grid:
                                self.grid_trading.loc[-1] = g  # adding a row
                                self.grid_trading.index = self.grid_trading.index + 1  # shifting index
                                self.grid_trading.sort_index(inplace=True)

                # check stoploss
                if self.price < self.stop_loss:
                    # stop grid, sell all
                    instant_limit_order(self.ftx_client, self.market_symbol, "sell",
                                        float(self.base_symbol_balance['free']))
                    sys.exit()

                # TRADE
                traded = 0
                cf = 0
                # check ta signal
                ta_buy = check_ta(self.market_symbol, self.timeframe_buy,
                                  self.ema1_len_buy, self.ema2_len_buy, name="buy")
                ta_sell = check_ta(self.market_symbol, self.timeframe_sell,
                                   self.ema1_len_sell, self.ema2_len_sell, name="sell")
                # BUY CHECK
                if ta_buy == 1:
                    pos_val = 0
                    # check grid above price
                    for i, r in self.grid_trading.iterrows():
                        if r['price'] >= self.market_info['ask'] and r['hold'] == 0 and r['hold_price'] == -1:
                            # add pos together
                            pos_val += r['value']
                            # update grid
                            self.grid_trading.iloc[i,
                                                   2] = r['value']/self.market_info['ask']
                            self.grid_trading.iloc[i,
                                                   3] = self.market_info['ask']
                    # buy
                    if pos_val != 0:
                        pos_unit = pos_val/self.market_info['ask']
                        instant_limit_order(
                            self.ftx_client, self.market_symbol, "buy", pos_unit)
                        traded = 1
                # SELL CHECK
                if ta_sell == 2:
                    pos_hold = 0
                    # check grid below price
                    for i, r in self.grid_trading.iterrows():
                        if r['hold'] > 0 and r['hold_price'] != -1 and self.price > r['price']:
                            # add pos together
                            pos_hold += r['hold']
                            # cf cal
                            cf += (self.price*r['hold']) - \
                                (r['hold_price']*r['hold'])
                            # update grid
                            self.grid_trading.iloc[i, 2] = 0
                            self.grid_trading.iloc[i, 3] = -1
                        # sell
                    if pos_hold != 0:
                        instant_limit_order(
                            self.ftx_client, self.market_symbol, "sell", pos_hold)
                        traded = 1

                # LOG
                if traded == 1:
                    # update grid.csv
                    self.grid_trading.to_csv('./public/grid_trading.csv')
                    # re tick
                    self.update_stats()
                    # update log
                    dt = datetime.datetime.now()
                    add_row(dt.strftime("%d/%m/%Y %H:%M:%S"),
                            self.price, self.nav, self.nav_pct, self.avg_buy_price, cf)
                    if cf > 0:
                        # transfer cf
                        self.ftx_client.subaccount_transfer(
                            self.quote_symbol, math.floor(cf), self.sub_account, "main")

                # print stats
                self.display_stats()
            except Exception as err:
                print(err)
            time.sleep(65)


bot = Bot('./public/grid.csv', "./config.ini")
print(bot.grid)
print(bot.grid_trading)
bot.run()

#future + option stretegy