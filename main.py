import os
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
import pandas as pd

# load config.ini
config = ConfigParser()
config.read('./public/config.ini')
# settings
testnet = int(config['binance']['testnet'])
print('testnet:', testnet, "\n")
if testnet == 1:
    base_url = config['binance']['testnet_url']
    api_key = config['binance']['api_key_testnet']
    secret_key = config['binance']['secret_key_testnet']
else:
    # load .env
    dotenv.load_dotenv('.env')
    base_url = config['binance']['url']
    api_key = os.environ.get("API_KEY")
    secret_key = os.environ.get("SECRET_KEY")


def req(method: str, url: str, params: dict[object, object] = {}, **kwargs):
    if 'auth' not in kwargs:
        kwargs['auth'] = False

    if kwargs['auth'] == True:
        # signature
        servertime = requests.get(
            base_url+"/api/v3/time").json()['serverTime']
        params['timestamp'] = servertime
        _params = urlencode(params)
        # hmac
        hashedsig = hmac.new(secret_key.encode('utf-8'), _params.encode('utf-8'),
                             hashlib.sha256).hexdigest()
        params['signature'] = hashedsig
    # request
    match method:
        case "GET":
            res = requests.get(url, params=params, headers={
                               "X-MBX-APIKEY": api_key})
        case "POST":
            res = requests.post(url, params=params, headers={
                "X-MBX-APIKEY": api_key})
    res = res.json()
    if "code" in res and res['code'] != 200:
        print(res, end="\n\n")
    return res


def get_balances(symbols: str):
    res = req("GET", base_url + "/api/v3/account", {}, auth=True)
    balances = res['balances']
    balances_dict = {}
    for s in symbols:
        for a in balances:
            if a['asset'] == s:
                balances_dict[s] = a
    return balances_dict


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
    elif type == "pyramid_increase":  # top small pos size => bottom bigger pos size
        if 'increase' not in kwargs:
            raise Exception('increase is missing')
        increase = kwargs['increase']
        for i in range(len(grid['price'])):
            if i > 0:
                value += increase
            grid['value'].append(value)
            grid['unit'].append(value/grid['price'][i])
        return grid
    elif type == "pyramid_multiply":  # top small pos size => bottom bigger pos size
        if 'multiply' not in kwargs:
            raise Exception('multiply  is missing')
        multiply = kwargs['multiply']
        for i in range(len(grid['price'])):
            if i > 0:
                value *= multiply
            grid['value'].append(value)
            grid['unit'].append(value/grid['price'][i])
        return grid

g = grid_gap(4000, 500, "pct", gap_pct=5)
g = grid_val(g, "pyramid_increase", 30, increase=10)
g = pd.DataFrame(g)
g.to_csv('grid.csv')
print(g)
