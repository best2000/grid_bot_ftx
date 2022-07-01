import csv

col = ["datetime", "price", "NAV", "NAV%", "avg_buy_price", "CF"]
with open('./public/log/trade_log.csv', 'w', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerow(col)


def add_row(datetime: str, price: float, nav: float, nav_pct: float, avg_buy_price: float, cf: float):
    with open('./public/log/trade_log.csv', 'a', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime, price, nav, nav_pct, avg_buy_price, cf])
