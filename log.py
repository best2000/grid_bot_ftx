import csv

col = ["datetime", "price", "NAV", "NAV%"]
with open('./public/log.csv', 'w', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerow(col)


def add_row(datetime: str, price: float, nav: float, nav_pct: float):
    with open('./public/log.csv', 'a', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime, price, nav, nav_pct])
