import os
import dotenv
from configparser import ConfigParser
from datetime import datetime
import asyncio
import datetime
import time
import pandas as pd
from ftx_client import FtxClient, instant_limit_order
from tech import check_ta
from log import *
import math

# load config.ini
config = ConfigParser()
config.read('./config.ini')
market_symbol = config['main']['market_symbol']
sub_account = config["main"]['sub_account']

# load .env
dotenv.load_dotenv('.env')
api_key = os.environ.get("API_FTX")
secret_key = os.environ.get("SECRET_FTX")

client = FtxClient(api_key,
                   secret_key, sub_account)


def get_balance(symbol):
    for a in client.get_balances():
        if a['coin'] == symbol:
            return a


# check market pair
client.get_single_market(market_symbol)

# init nav
base_symbol = market_symbol.split('/')[0]
quote_symbol = market_symbol.split('/')[1]
base_symbol_balance = get_balance(base_symbol)
quote_symbol_balance = get_balance(quote_symbol)
init_nav = float(0 if not base_symbol_balance else base_symbol_balance['usdValue']) + float(
    0 if not quote_symbol_balance else quote_symbol_balance['usdValue'])

# read csv to pandas
grid = pd.read_csv('./public/grid.csv', sep=',', index_col=0)

# check stablecoin balance amount
grid_posval_sum = grid['value'].sum()
if (int(config['main']['check_funds'])) & (float(0 if not quote_symbol_balance else quote_symbol_balance['usdValue']) < grid_posval_sum):
    raise Exception("Insufficient funds!")


while True:
    try:
        # check exhange pair and price
        market_info = client.get_single_market(market_symbol)
        if market_info['enabled'] == False:
            raise Exception("FTX suspended trading!")
        price = market_info['price']
        # cal nav
        base_symbol_balance = get_balance(base_symbol)
        quote_symbol_balance = get_balance(quote_symbol)
        nav = float(0 if not base_symbol_balance else base_symbol_balance['usdValue']) + float(
            0 if not quote_symbol_balance else quote_symbol_balance['usdValue'])
        nav_pct = nav/init_nav*100
        # cal grid pos pct
        grid_pos = grid['hold'].to_list()
        for i in range(len(grid_pos)):
            if grid_pos[i] == 0:
                grid_cpos = i
                grid_pos_pct = i / len(grid_pos)*100
                break

        # TRADE
        t = 0
        cf = 0
        # check ta signal
        ta = check_ta(market_symbol, config['ta']['timeframe'], int(
            config['ta']['ema1_len']), int(config['ta']['ema2_len']))
        # SELL CHECK
        if ta == 2:
            pos_hold = 0
            # check grid below price
            for i, r in grid.iterrows():
                if r['hold'] > 0 and r['hold_price'] != -1 and price > r['price']:
                    # add pos together
                    pos_hold += r['hold']
                    # cf cal
                    cf += (price*r['hold'])-(r['hold_price']*r['hold'])
                    # update grid
                    grid.iloc[i, 2] = 0
                    grid.iloc[i, 3] = -1
                # sell
            if pos_hold != 0:
                instant_limit_order(
                    client, market_symbol, "sell", pos_hold)
                t = 1
        elif ta == 1:  # BUY CHECK
            pos_val = 0
            # check grid above price
            for i, r in grid.iterrows():
                if r['price'] >= market_info['ask'] and r['hold'] == 0 and r['hold_price'] == -1:
                    # add pos together
                    pos_val += r['value']
                    # update grid
                    grid.iloc[i, 2] = r['value']/market_info['ask']
                    grid.iloc[i, 3] = market_info['ask']
             # buy
            if pos_val != 0:
                pos_unit = pos_val/market_info['ask']
                instant_limit_order(client, market_symbol, "buy", pos_unit)
                t = 1

        # LOG
        if t == 1:
            # update grid.csv
            grid.to_csv('./public/grid.csv')
            # cal nav
            base_symbol_balance = get_balance(base_symbol)
            quote_symbol_balance = get_balance(quote_symbol)
            nav = float(0 if not base_symbol_balance else base_symbol_balance['usdValue']) + float(
                0 if not quote_symbol_balance else quote_symbol_balance['usdValue'])
            nav_pct = nav/init_nav*100
            # update log
            dt = datetime.datetime.now()
            add_row(dt.strftime("%d/%m/%Y %H:%M:%S"),
                    price, nav, nav_pct, cf)
            if cf > 0:
                client.subaccount_transfer(
                    quote_symbol, math.floor(cf), sub_account, "main")

        # PRINT---
        os.system('cls' if os.name == 'nt' else 'clear')
        print("--------------------")
        print("[CONFIG]")
        print("market_symbol:", market_symbol)
        print("sub_account:", sub_account)
        print("grid_zone:", round(
            grid.iloc[-1, 0], 2), "=>", grid.iloc[0, 0])
        print("grid_posval_sum:", grid_posval_sum)
        print("-------------------")
        print("[STATUS]")
        print("{}: {}".format(market_symbol, price))
        print(base_symbol+" balance: " +
              str(float(0 if not base_symbol_balance else base_symbol_balance['free'])))
        print(quote_symbol+" balance: " +
              str(float(0 if not quote_symbol_balance else quote_symbol_balance['free'])))
        print("NAV: "+str(round(nav, 2))+"/" +
              str(round(init_nav, 2))+" ["+str(int(nav_pct))+"%]")
        print("grid_pos: "+str(grid_cpos)+"/"+str(len(grid_pos)) +
              " ["+str(int(grid_pos_pct))+"%]")
    except Exception as err:
        print(err)
    print("--------------------")
