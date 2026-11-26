"""Mistake: discard the fraction of a pound of remaining allowance."""

import json
import sys

AMOUNTS = (6475, 6475, 7475, 8105, 9440, 10000, 10600, 11000, 11500, 11850,
           12500, 12500, 12570, 12570, 12570, 12570, 12570, 12570, 12570, 12570, 12570, 12570)


def allowance(tax_year_start, adjusted_net_income_pounds):
    full = AMOUNTS[tax_year_start - 2009]
    excess = max(0, adjusted_net_income_pounds - 100000) if tax_year_start >= 2010 else 0
    remaining = max(0, full * 2 - excess)
    return remaining // 2


if __name__ == "__main__":
    print(json.dumps({"allowance_pounds": allowance(**json.load(sys.stdin))}))
