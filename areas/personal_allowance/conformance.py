"""Publish and sample the allowance in whole pounds, for the supplier cases and the differential run."""

from decimal import getcontext

from presentation import money
from .calculator import compute
from .parser import year_label

VENDOR = "pa"
OUTPUT = "allowance_pounds"


INPUT = {"tax_year_start": {"type": "integer", "minimum": 2009, "maximum": 2030},
         "adjusted_net_income_pounds": {"type": "integer", "minimum": 0}}


def published(rows):
    seen = set()
    for r in rows:
        if r["quantity"] != "allowance (£)":
            continue
        year = r["tax_year_start"]
        pounds, pence = divmod(r["adjusted_net_income_pence"], 100)
        if pence:
            raise ValueError("Supplier income must be in whole pounds")
        if (year, pounds) in seen:
            continue
        seen.add((year, pounds))
        desc = f"income {money(pounds)}"
        if r["comparison"] == "govuk_ani_example":
            desc += ": GOV.UK's worked example"
        elif r["comparison"] == "whole_pound_nil_points":
            desc = "£1 below the income where the allowance reaches zero"
        elif r["comparison"] == "nil_points_by_year":
            desc = "income where the allowance reaches zero"
        yield dict(description=f"{year_label(year)}, {desc}",
                   input=dict(tax_year_start=year, adjusted_net_income_pounds=pounds),
                   expected={OUTPUT: r["expected"]}, provision=r["provision"].replace("s35(2)-(3)", "s35(2) and s35(3)"),
                   also_proved=r.lean)


def sample(rules, rng):
    years = list(map(int, rules["years"]))
    taper = rules["taper"]
    limit, step = taper["income_limit"], taper["divisor"]

    def row(year, pounds):
        cite = rules["years"][str(year)]["citation"]
        if year >= taper["first_year"] and pounds > limit:
            cite += "; " + taper["citation"]
        return dict(input=dict(tax_year_start=year, adjusted_net_income_pounds=pounds),
                    expected={OUTPUT: compute(pounds, year, rules)}, provision=cite)

    rng.shuffle(years)
    for year in years:
        yield row(year, 0)
        yield row(year, 1)
        if year == 2026:
            # Tax starts after the allowance. The basic band ends before tapering starts.
            full = rules["years"][str(year)]["amount"]
            for edge in (full, full + rules["tax"]["basic_limit_pounds"]):
                for delta in (-1, 0, 1):
                    yield row(year, edge + delta)
        if year >= taper["first_year"]:
            nil = limit + rules["years"][str(year)]["amount"] * step
            for edge in (limit, limit + step, nil):
                for delta in (-1, 0, 1):
                    yield row(year, edge + delta)
    while True:
        year = rng.choice(years)
        yield row(year, rng.randrange(10 ** rng.randint(1, getcontext().prec - 2)))
        if year >= taper["first_year"]:
            full = rules["years"][str(year)]["amount"]
            edge = limit + step * rng.randint(1, full)
            for delta in (-1, 0, 1):
                yield row(year, edge + delta)
