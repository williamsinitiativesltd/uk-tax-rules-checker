"""Sample each dated Table A and compare the duty on its transaction price."""

from datetime import date
from decimal import Decimal, getcontext

from area import DAY, rule_periods
from presentation import long_date, money
from .calculator import compute

VENDOR = "sdlt"
OUTPUT = "tax_pounds"
INPUT = {"effective_date": {"type": "string", "format": "date"},
         "price_pounds": {"type": "number", "minimum": 0, "multipleOf": 0.01}}


def published(rows):
    for r in rows:
        price = int(r["price_gbp"])
        description = "worked example" if r.lean else "band boundary check"
        yield dict(description=f"{long_date(r['date'])}, {money(price)}: {description}",
                   input=dict(effective_date=r["date"], price_pounds=price),
                   expected={OUTPUT: r["expected"]}, provision=r["provision"], also_proved=r.lean)


def sample(rules, rng):
    periods = rule_periods(rules)
    rng.shuffle(periods)

    def row(day, price):
        result = compute(price, day, rules)
        return dict(input=dict(effective_date=day.isoformat(), price_pounds=price),
                    expected={OUTPUT: result.total}, provision=result.version_citation)

    for start, end, version in periods:
        last = end - DAY if end else date.max
        for day in dict.fromkeys((start, min(start + DAY, last), last)):
            yield row(day, version["bands"][-1]["lower"])
        for band in version["bands"]:
            lower = band["lower"]
            edges = [lower]
            rate = int(Decimal(band["rate"]) * 100)
            if rate:
                # First pound where this band's contribution reaches another whole pound.
                edges.append(lower + (100 + rate - 1) // rate)
            for edge in edges:
                for delta in (-1, 0, 1):
                    if edge + delta >= 0:
                        yield row(start, edge + delta)

    while True:
        start, end, version = rng.choice(periods)
        last = end - DAY if end else date.max
        day = start + rng.randint(0, (last - start).days) * DAY
        yield row(day, rng.randrange(10 ** rng.randint(1, getcontext().prec - 2)))

        band = rng.choice([band for band in version["bands"] if Decimal(band["rate"])])
        rate = int(Decimal(band["rate"]) * 100)
        lower = band["lower"]
        width = (band["upper"] or 2 * band["lower"]) - lower
        pounds = rng.randint(1, width * rate // 100)
        edge = lower + (pounds * 100 + rate - 1) // rate
        for delta in (-1, 0, 1):
            yield row(day, edge + delta)
