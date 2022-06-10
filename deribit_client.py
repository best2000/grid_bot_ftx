from typing import Optional, Dict, Any
from requests import Request, Session, Response
import pandas as pd
import dotenv
import os


class DeribitClient:
    _ENDPOINT = "https://www.deribit.com/api/v2/"

    def __init__(self, client_id=None, client_secret=None, subaccount_name=None) -> None:
        self._session = Session()
        self._client_id = client_id
        self._client_secret = client_secret
        self._subaccount_name = subaccount_name
        self._token = None
        self._refresh_token = None

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, json=params)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('DELETE', path, json=params)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, self._ENDPOINT + path, **kwargs)
        request.headers['Authorization'] = f"Bearer {self._token}"
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _process_response(self, response: Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if 'error' in data:
                raise Exception(data['error'])
            return data['result']

    def auth(self) -> dict:
        res = self._get(
            f'public/auth?client_id={self._client_id}&client_secret={self._client_secret}&grant_type=client_credentials')
        self._token = res['access_token']
        self._refresh_token = res['refresh_token']
        return True

    def refresh_token(self) -> dict:
        res = self._get(
            f'public/auth?refresh_token={self._refresh_token}&grant_type=refresh_token')
        self._token = res['access_token']
        self._refresh_token = res['refresh_token']
        return True

    def get_instruments(self, symbol: str, expired: str, kind: str) -> dict:
        return self._get(f'public/get_instruments?currency={symbol}&expired={expired}&kind={kind}')

    def get_account_summary(self, symbol: str, extended: str) -> dict:
        return self._get(f'private/get_account_summary?currency={symbol}&extended={extended}')

    def get_order_book(self, depth: int, instrument_name: str) -> dict:
        return self._get(f'public/get_order_book?depth={depth}&instrument_name={instrument_name}')

    def buy_market_limit(self, amount: float, instrument_name: str):
        return self._get(f'private/buy?amount={amount}&instrument_name={instrument_name}&type=market_limit')

    def sell_market_limit(self, amount: float, instrument_name: str):
        return self._get(f'private/sell?amount={amount}&instrument_name={instrument_name}&type=market_limit')


def instant_limit(client: DeribitClient, symbol: str, type: str, size: float):
    ob = client.get_order_book(3, symbol)
    if type == "sell":
        best_price = ob['best_bid_price']
        if size < ob['best_bid_amount']:
            c.sell_market_limit(size, symbol)
            return
    if type == "buy":
        best_price = ob['best_ask_price']
        if size < ob['best_ask_amount']:
            c.buy_market_limit(size, symbol)
            return


# load .env
dotenv.load_dotenv('.env')
api_key = os.environ.get("API_DERIBIT")
secret_key = os.environ.get("SECRET_DERIBIT")

c = DeribitClient(api_key, secret_key)
# c.auth()
# c.refresh_token()
#r = c.get_account_summary("SOL", "false")
#instant_limit(c, "SOL-24JUN22-20-P", "sell", 1)


def long_put_cal(symbol: str, size: float = 1):
    op = c.get_instruments(symbol, "false", "option")
    options = {}
    for o in op:
        for i in o:
            if i not in options:
                options[i] = []
            options[i].append(o[i])

    df = pd.DataFrame(options)
    df = df.drop(columns=['creation_timestamp', 'tick_size', 'taker_commission',
                          'settlement_currency', 'counter_currency', 'quote_currency', 'block_trade_commission', 'base_currency', 'contract_size', 'instrument_id', 'kind', 'price_index', 'rfq', 'maker_commission', 'settlement_period'])
    df = df.sort_values(by='strike', ascending=True)
    df = df.reset_index(drop=True)
    #df['expiration_timestamp'] = pd.to_datetime(df['expiration_timestamp'], unit='ms')
    # df.to_csv("options.csv")
    min_trade_amount = df.iloc[0, 2]
    print(min_trade_amount)

    df = df.query("option_type == 'put'")

    for i, r in df.iterrows():
        ob = c.get_order_book(3, r['instrument_name'])
        if ob['best_ask_price'] != 0 :
            # now
            price = ob['underlying_price']
            strike = r['strike']
            premium_price = ob['best_ask_price']
            premium_cost = (premium_price*price)*size

            # future
            break_even_price = strike-(premium_cost/size)
            #future_price = 10
            #pos_profit = size*(strike-future_price)
            # if pos_profit > premium_cost:
            #   profit = pos_profit-premium_cost

            # print
            print(r['instrument_name'])
            print("-------------------")
            print("price:", price)
            print("strike:", strike)
            print("premium_price:", premium_price)
            print("size:", size)
            print("premium_cost:", premium_cost)
            print("break_even_price:", break_even_price)
            print("-------------------")


long_put_cal("SOL",6)
