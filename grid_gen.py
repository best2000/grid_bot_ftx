from configparser import NoOptionError
from msilib import type_binary
import typer
import mplfinance as mpf
import dotenv
import os
import ccxt
import matplotlib.pyplot as plt
import pandas as pd
from configparser import ConfigParser

# load config.ini
config = ConfigParser()
config.read('./config.ini')
cut_min = int(config['grid_gap_pct']['cut_min'])


def grid_gap(lower_limit_price: float, upper_limit_price: float, gtype: str = "pct", **kwargs):
    if gtype == "pct":  # top low frequency gap => bottom high frequency gap
        if 'gap_pct' not in kwargs:
            raise Exception('gap_pct is missing')
        gap_pct = kwargs['gap_pct']
        grid = {"price": []}
        grid_price = upper_limit_price
        grid['price'].append(upper_limit_price)
        while True:
            grid_price = grid_price*(100-gap_pct)/100
            if grid_price < lower_limit_price:
                if cut_min == 0:
                    grid['price'].append(grid_price)
                else:
                    grid['price'].append(lower_limit_price)
                break
            grid['price'].append(grid_price)
        return grid
    elif gtype == "fix":  # equally gap
        if 'div' not in kwargs:
            raise Exception('div is missing')
        div = kwargs['div']
        gap = (upper_limit_price-lower_limit_price)/div
        grid = {"price": []}
        for i in range(div+1):
            price = upper_limit_price-(gap*i)
            grid['price'].append(price)
        return grid


def grid_val(grid: dict, gtype: str, value, **kwargs):
    grid['value'] = []
    grid['hold'] = []
    if gtype == "fix":  # fix value grid
        for p in grid['price']:
            grid['value'].append(value)
            grid['hold'].append(0)
        return grid
    elif gtype == "pyramid":  # top small pos size => bottom bigger pos size
        if 'increase' not in kwargs:
            raise Exception('increase is missing')
        increase = kwargs['increase']
        for i in range(len(grid['price'])):
            if i > 0:
                value += increase
            grid['value'].append(value)
            grid['hold'].append(0)
        return grid
    elif gtype == "pyramid_invert":  # top small pos size => bottom bigger pos size
        if 'decrease' not in kwargs:
            raise Exception('decrease is missing')
        decrease = kwargs['decrease']
        for i in range(len(grid['price'])):
            if i > 0:
                value -= decrease
            grid['value'].append(value)
            grid['hold'].append(0)
        return grid

def plot_img(grid: pd.DataFrame, symbol: str, timeframe: str, limit: int = 2000):
    def get_candles(symbol: str, timeframe: str, limit: int):
        # load .env
        dotenv.load_dotenv('.env')
        apiKey = os.environ.get("API_KEY")
        secret = os.environ.get("SECRET_KEY")
        exchange = ccxt.ftx(
            {'apiKey': apiKey, 'secret': secret, 'enableRateLimit': True})

        candles = exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(
            candles, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        df = df.astype(float)
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df = df.set_index('datetime')
        return df

    # plot grid
    plt.xlim(grid.iloc[0:-1, 1].min()-2, grid.iloc[0:-1, 1].max()+2)
    plt.grid(axis='x')
    for i, r in grid.iterrows():
        plt.hlines(y=r['price'], xmin=0, xmax=r['value'])
    plt.ylabel("Price")
    plt.xlabel("Value")
    plt.title("Grid position value")
    plt.savefig('./public/grid.jpeg')

    # plot grid+price
    df = get_candles(symbol, timeframe, limit)
    hl = dict(hlines=grid['price'].to_list(), colors=[
              'g'], linestyle='-.', linewidths=(1))
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff00ff', inherit=True)
    s = mpf.make_mpf_style(
        base_mpl_style=['dark_background', 'bmh'], marketcolors=mc)
    # plot fig
    mpf.plot(df, type='line', volume=False,
             title="\n\n\nGrid ("+symbol+" "+timeframe+")", style=s, hlines=hl, savefig='./public/grid+candles.png')


# CLI
cli = typer.Typer()


@cli.command()
def gen(min_zone: float, max_zone: float, gap_type: str, pos_type: str, pos_val: float, inc: float = None, dec: float = None, gap_pct: float = None, div: int = None):
    global g
    # gap
    if gap_type == "fix":
        if div == None:
            typer.echo("missing --div")
            return
        g = grid_gap(min_zone, max_zone, gap_type, div=div)
    elif gap_type == "pct":
        if gap_pct == None:
            typer.echo("missing --gap-pct")
            return
        g = grid_gap(min_zone, max_zone, gap_type, gap_pct=gap_pct)
    else:
        typer.echo("invalid gap_type")
    # position size
    if pos_type == "fix":
        g = grid_val(g, pos_type, pos_val)
    elif pos_type == "pyramid":
        if inc == None:
            typer.echo("missing --inc")
            return
        g = grid_val(g, pos_type, pos_val, increase=inc)
    elif pos_type == "pyramid_invert":
        if dec == None:
            typer.echo("missing --dec")
            return
        g = grid_val(g, pos_type, pos_val, decrease=dec)
    else:
        typer.echo("invalid pos_type")

    # save to grid.csv
    g = pd.DataFrame(g)
    g.to_csv('./public/grid.csv')
    # plot grid val
    plt.xlim(g.iloc[0:-1, 1].min()-2, g.iloc[0:-1, 1].max()+2)
    plt.grid(axis='x')
    for i, r in g.iterrows():
        plt.hlines(y=r['price'], xmin=0, xmax=r['value'])
    plt.ylabel("Price")
    plt.xlabel("Value")
    plt.title("Grid position value")
    plt.savefig('./public/grid.jpeg')
    # log
    typer.echo(g)
    typer.echo("val_sum: " + str(g['value'].sum()))
    typer.echo("plz check ./public/grid.csv")


@cli.command()
def plot(market_symbol: str, timeframe: str, limit: int):
    # read csv to pandas
    g = pd.read_csv('./public/grid.csv', sep=',', index_col=0)
    # plot fig
    plot_img(g, market_symbol, timeframe, limit)


if __name__ == '__main__':
    cli()
