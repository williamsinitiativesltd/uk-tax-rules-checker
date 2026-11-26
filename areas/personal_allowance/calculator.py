"""ANI is supplied in pounds. The allowance is in pounds and example tax in pence."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

from area import load_rules


def applicable_taper(year, rules):
    taper = rules["taper"]
    return taper if year >= taper["first_year"] else None


def compute(income, year, rules=None):
    rules = load_rules(Path(__file__).parent) if rules is None else rules
    if type(year) is not int or str(year) not in rules["years"]:
        raise ValueError(f"No personal allowance for tax year {year}")
    try:
        value = Decimal(str(income))
        if not value.is_finite() or value < 0 or value != value.quantize(Decimal(".01")):
            raise ValueError("Adjusted net income must be a non-negative amount in pounds and pence")
    except InvalidOperation as exc:
        raise ValueError("Invalid adjusted net income") from exc
    full = rules["years"][str(year)]["amount"]
    taper = applicable_taper(year, rules)
    if taper is None:
        return full
    excess = max(0, int(value * 100) - taper["income_limit"] * 100)
    # Rounding the remainder up is equivalent to taking only whole pounds off.
    return max(0, full - excess // (100 * taper["divisor"]))


def tax2026(pence, rules, bands):
    allowance = compute(Decimal(pence) / 100, 2026, rules)
    return tax_with_allowance(pence, allowance, bands)


def tax_with_allowance(pence, allowance, bands):
    taxable = max(0, pence - 100 * allowance)
    total = lower = 0
    for upper, rate in bands:
        stop = taxable if upper is None else min(taxable, upper * 100)
        total += max(0, stop - lower) * rate // 100
        lower = stop
    return total
