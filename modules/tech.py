import pandas as pd
import ta
import mplfinance as mpf
import ccxt
import dotenv
import os

# load .env
dotenv.load_dotenv('.env')
apiKey = os.environ.get("API_KEY")
secret = os.environ.get("SECRET_KEY")

exchange = ccxt.ftx(
    {'apiKey': apiKey, 'secret': secret, 'enableRateLimit': True})


def get_candles(symbol: str, timeframe: str, limit: int = 1000):  # 1h 4h 1d
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(
        candles, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df = df.astype(float)
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    #df = df.set_index('time')
    #df.index = pandas.to_datetime(df.index, unit='ms')
    return df


def signal(df: pd.DataFrame, ema1_len=10, ema2_len=20):
    # calculate indicator
    ema1 = ta.trend.EMAIndicator(df['close'], window=ema1_len)
    df['ema1'] = ema1.ema_indicator()
    ema2 = ta.trend.EMAIndicator(df['close'], window=ema2_len)
    df['ema2'] = ema2.ema_indicator()

    # signal
    ema_cross = []
    for i, r in df.iterrows():
        # check ema cross
        if i > 0:  # skip index 0
            ema1_l = df.iloc[i-1, 6]
            ema2_l = df.iloc[i-1, 7]
            # cross up = 1
            if (ema1_l < ema2_l) & (r['ema1'] > r['ema2']):
                ema_cross.append(1)
            # cross down = 2
            elif (ema1_l > ema2_l) & (r['ema1'] < r['ema2']):
                ema_cross.append(2)
            else:
                ema_cross.append(0)
        else:
            ema_cross.append(0)
    df['signal'] = pd.Series(ema_cross)
    return df


def plot(df: pd.DataFrame, symbol: str, timeframe: str):
    # setup
    sig_up = df.query('signal == 1')
    sig_down = df.query('signal == 2')
    vl_up = dict(
        vlines=sig_up["datetime"].tolist(), linewidths=1, colors='g')
    vl_down = dict(
        vlines=sig_down["datetime"].tolist(), linewidths=1, colors='r')
    df = df.set_index('datetime')

    # style
    # Create my own `marketcolors` to use with the `nightclouds` style:
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff00ff', inherit=True)

    # Create a new style based on `nightclouds` but with my own `marketcolors`:
    s = mpf.make_mpf_style(
        base_mpl_style=['dark_background', 'bmh'], marketcolors=mc)

    # Plot
    mpf.plot(df, type='line', volume=False,
             title="\n"+symbol+" "+timeframe+"\nBottom Signals", style=s, vlines=vl_up)
    mpf.plot(df, type='line', volume=False,
             title="\n"+symbol+" "+timeframe+"\nTop Signals", style=s, vlines=vl_down)


def check_ta(symbol: str, timeframe: str,  ema1_len: int = 5, ema2_len: int = 10, limit: int = 100, **kwargs) -> pd.DataFrame:
    df = get_candles(symbol, timeframe, limit)
    df = signal(df, ema1_len, ema2_len)
    if 'name' in kwargs:
        df.to_csv("./public/ta_"+str(kwargs['name'])+".csv")
    else:
        df.to_csv("./public/ta.csv")
    return df


"""
symbol = "FTT/USDT"
timeframe = '4h'
df = get_candles(symbol, timeframe, 1000)
print(df)
df = signal(df)
# df.to_csv("t.csv")
print(df)
plot(df, symbol, timeframe)
"""
#df = get_candles("FTT/USDT", '1m', 1000)
# print(signal(df).tail(2))
# EMA10 & 15 cross + rsi backward check + chg%
