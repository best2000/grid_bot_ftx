import os
import dotenv
from configparser import ConfigParser
from datetime import datetime
import asyncio
import datetime
import time
import pandas as pd
from ftx_client import FtxClient
from tech import check_ta
from log import *

# load config.ini
config = ConfigParser()
config.read('./config.ini')
market_symbol = config['main']['market_symbol']
sub_account = config["main"]['sub_account']

# load .env
dotenv.load_dotenv('.env')
api_key = os.environ.get("API_KEY")
secret_key = os.environ.get("SECRET_KEY")

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


async def wait():
    bar = [
        " | ",
        " / ",
        " ─ ",
        " \ ",
    ]
    i = 0

    while True:
        print(bar[i % len(bar)]+str(int(time.time())), end="\r")
        await asyncio.sleep(0.1)
        i += 1


async def loop():
    asyncio.create_task(wait())
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
            grid_pos = grid['position'].to_list()
            for i in range(len(grid_pos)):
                if grid_pos[i] == 0:
                    grid_cpos = i
                    grid_pos_pct = i / len(grid_pos)*100
                    break

            # check ta signal
            ta = check_ta(
                market_symbol, config['ta']['timeframe'], int(config['ta']['ema1_len']), int(config['ta']['ema2_len']))
            if ta > 0:
                new_cf = 0
                pos_val = 0
                if ta == 1:
                    # check grid above price
                    for i, r in grid.iterrows():
                        if (r['price'] >= price) & (r['position'] == 0):
                            # add pos together
                            pos_val += r['value']
                            # update grid
                            grid.iloc[i, -1] = 1
                        else:
                            break
                    # buy
                    if pos_val != 0:
                        pos_unit = pos_val/price
                        client.place_order(
                            market_symbol, "buy", None, pos_unit, "market")
                elif ta == 2:
                    # check grid below price (only brought)
                    for i, r in grid.iterrows():
                        if (price > r['price']) & (r['position'] == 1):
                            # add pos together
                            pos_val += r['value']
                            # update grid
                            grid.iloc[i, -1] = 0
                        # sell
                    if pos_val != 0:
                        pos_unit = pos_val/price
                        # sell to USD
                        client.place_order(base_symbol+"/USD", "sell",
                                           None, pos_unit, "market")
                        # cal new_cf
                        new_cf = pos_val
                # update grid.csv
                grid.to_csv('./public/grid.csv')
                # update log
                dt = datetime.datetime.now()
                add_row(dt.strftime("%d/%m/%Y %H:%M:%S"),
                        price, nav, nav_pct, new_cf)
                # cal nav
                base_symbol_balance = get_balance(base_symbol)
                quote_symbol_balance = get_balance(quote_symbol)
                nav = float(0 if not base_symbol_balance else base_symbol_balance['usdValue']) + float(
                    0 if not quote_symbol_balance else quote_symbol_balance['usdValue'])
                nav_pct = nav/init_nav*100

            # PRINT---
            os.system('cls' if os.name == 'nt' else 'clear')
            print("--------------------")
            print("[CONFIG]")
            print("market_symbol:", market_symbol)
            print("sub_account:", sub_account)
            print("grid_zone:", grid.iloc[-1, 0], "=>", grid.iloc[0, 0])
            print("grid_posval_sum:", grid_posval_sum)
            print("-------------------")
            print("[STATUS]")
            print(market_symbol+": "+str(price))
            print(base_symbol+" balance: " +
                  str(float(0 if not base_symbol_balance else base_symbol_balance['free'])))
            print(quote_symbol+" balance: " +
                  str(float(0 if not quote_symbol_balance else quote_symbol_balance['free'])))
            print("NAV: "+str(round(nav, 2))+"/" +
                  str(round(init_nav, 2))+" ["+str(int(nav_pct))+"%]")
            print("grid_pos: "+str(grid_cpos)+"/"+str(len(grid_pos)) +
                  " ["+str(int(grid_pos_pct))+"%]")
            print("avg_pos_price:", (init_nav-float(0 if not quote_symbol_balance else quote_symbol_balance['free']))/float(
                0.1 if not base_symbol_balance else base_symbol_balance['free']))
        except Exception as err:
            print(err)
        print("--------------------")
        print("next_wake:", int(time.time())+300)
        await asyncio.sleep(300)

asyncio.run(loop())

# profit compound/keep, technical รวบโซน
# net ass val (NAV), dd, cash flow per ..., cumulative
