import matplotlib.pyplot as plt
import pandas as pd


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
    grid['position'] = []
    for i in range(len(grid['price'])):
        grid['position'].append(0)
    return grid

def plot(grid):
    plt.xlim(grid.iloc[0:-1, 1].min()-1, grid.iloc[0:-1, 1].max()+1)
    plt.grid(axis='x')
    for i, r in grid.iterrows():
        plt.hlines(y=r['price'], xmin=0, xmax=r['value'])
    plt.ylabel("Price")
    plt.xlabel("Value")
    plt.savefig('./public/grid.jpeg')

# generate grid.csv
#grid gap
g = grid_gap(2500, 1000, "pct", gap_pct=5)
#grid position value
g = grid_val(g, "pyramid", 10, increase=1)
#fill position status with default value
g = fill_buy(g)
#save to grid.csv
g = pd.DataFrame(g)
g.to_csv('./public/grid.csv')

print(g)
print("pos_val_sum:", g['value'].sum())
plot(g)
