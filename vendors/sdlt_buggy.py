"""Mistake: apply the highest applicable rate to the entire price."""

from decimal import Decimal
import json
import sys


def schedule(day):
    if day == "2014-12-03":
        return [(0, 0), (125000, 1), (250000, 3), (500000, 4), (1000000, 5), (2000000, 7)]
    if "2020-07-08" <= day <= "2021-06-30":
        lower = [(0, 0), (500000, 5)]
    elif "2021-07-01" <= day <= "2021-09-30" or "2022-09-23" <= day <= "2025-03-31":
        lower = [(0, 0), (250000, 5)]
    else:
        lower = [(0, 0), (125000, 2), (250000, 5)]
    return lower + [(925000, 10), (1500000, 12)]


def tax(effective_date, price_pounds):
    price = int(price_pounds * 100)
    for lower, rate in reversed(schedule(effective_date)):
        if price > lower * 100:
            return price * rate // 10000
    return 0


if __name__ == "__main__":
    print(json.dumps({"tax_pounds": tax(**json.load(sys.stdin, parse_float=Decimal))}))
