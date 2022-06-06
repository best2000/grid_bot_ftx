import matplotlib.pyplot as plt
import pandas as pd

# read csv to pandas
grid = pd.read_csv('./public/grid.csv', sep=',', index_col=0)

plt.xlim(grid.iloc[0:-1, 1].min()-2, grid.iloc[0:-1, 1].max()+2)
plt.grid(axis='x')
for i, r in grid.iterrows():
    plt.hlines(y=r['price'], xmin=0, xmax=r['value'])
plt.ylabel("Price")
plt.xlabel("Value")
plt.savefig('./public/grid.jpeg')
