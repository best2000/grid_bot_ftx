import os
from time import sleep
import dotenv
from numpy import multiply
import requests
import hashlib
import hmac
from urllib.parse import urlencode
from configparser import ConfigParser
import json
from datetime import datetime
import asyncio
import time
import pandas as pd
from ftx_client import FtxClient
from tech import check_ta


# load config.ini
config = ConfigParser()
config.read('./public/config.ini')
market_symbol = config['config']['market_symbol']
sub_account = config["config"]['sub_account']

# load .env
dotenv.load_dotenv('.env')
api_key = os.environ.get("API_KEY")
secret_key = os.environ.get("SECRET_KEY")

client = FtxClient(api_key,
                   secret_key, sub_account)


def grid_gap(upper_limit_price: float, lower_limit_price: float, type: str = "pct", **kwargs):
    if type == "pct":  # top low frequency gap => bottom high frequency gap
        if 'gap_pct' not in kwargs:
            raise Exception('gap_pct is missing')
        gap_pct = kwargs['gap_pct']
        grid = {"price": []}
        grid_price = upper_limit_price
        grid['price'].append(upper_limit_price)
        while True:
            grid_price = grid_price*(100-gap_pct)/100
            if grid_price < lower_limit_price:
                grid['price'].append(lower_limit_price)
                break
            grid['price'].append(grid_price)

        return grid
    elif type == "fix":  # equally gap
        if 'grid_count' not in kwargs:
            raise Exception('grid_count is missing')
        grid_count = kwargs['grid_count']
        gap = (upper_limit_price-lower_limit_price)/grid_count
        grid = {"price": []}
        for i in range(grid_count+1):
            price = upper_limit_price-(gap*i)
            grid['price'].append(price)
        return grid


def grid_val(grid: dict, type: str, value, **kwargs):
    grid['value'] = []
    grid['unit'] = []
    if type == "fix":  # fix value grid
        for p in grid['price']:
            grid['value'].append(value)
            grid['unit'].append(value/p)
        return grid
    elif type == "pyramid":  # top small pos size => bottom bigger pos size
        if 'increase' not in kwargs:
            raise Exception('increase is missing')
        increase = kwargs['increase']
        for i in range(len(grid['price'])):
            if i > 0:
                value += increase
            grid['value'].append(value)
            grid['unit'].append(value/grid['price'][i])
        return grid
    elif type == "pyramid_invert":  # top small pos size => bottom bigger pos size
        if 'decrease' not in kwargs:
            raise Exception('decrease is missing')
        decrease = kwargs['decrease']
        for i in range(len(grid['price'])):
            if i > 0:
                value -= decrease
            grid['value'].append(value)
            grid['unit'].append(value/grid['price'][i])
        return grid


def fill_buy(grid):
    grid['buy'] = []
    for i in range(len(grid['price'])):
        grid['buy'].append(0)
    return grid


# generate grid.csv
g = grid_gap(100, 5, "pct", gap_pct=5)
g = grid_val(g, "fix", 10, increase=1)
g = fill_buy(g)
g = pd.DataFrame(g)
g.to_csv('./public/grid.csv')

# read csv to pandas
grid = pd.read_csv('./public/grid.csv', sep=',', index_col=0)

print(grid)
print(grid['value'].sum())


async def wait():
    bar = [
        " | sleeping   ",
        " / sleeping.  ",
        " ─ sleeping.. ",
        " \ sleeping...",
    ]
    i = 0

    while True:
        print(bar[i % len(bar)], end="\r")
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

            # check ta signal
            ta = check_ta(market_symbol, '1h', 5, 10)
            if ta == 1:
                # check grid above price
                # add pos together and buy
                print("รวบซื้อข้างบน")
            elif ta == 2:
                # check grid below price (only brought)
                # sell pos amount
                print("รวบขายข้างล่าง")

            # PRINT---
            os.system('cls' if os.name == 'nt' else 'clear')
            print("--------------------")
            print("[CONFIG]")
            print("market_symbol:", market_symbol)
            print("sub_account:", sub_account)
            print("-------------------")
            print("[STATUS]")
            print(market_symbol+": "+str(price))
            print("DD:")
            print("CF:")
            print("--------------------")
        except Exception as err:
            print(err)
        await asyncio.sleep(120)

asyncio.run(loop())

# profit compound/keep, technical รวบโซน
# net ass val (NAV), dd, cash flow per ..., cumulative
