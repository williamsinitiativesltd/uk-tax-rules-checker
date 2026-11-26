"""Standard residential Stamp Duty Land Tax (Finance Act 2003 s55, Table A) as tested, traceable code.

The rates live in rules.json, each version dated and cited. This module holds no rate: it picks the
version for the effective date, applies its whole-price or slice rates and returns a cited trace.

Not modelled (the code has no input for them, so the caller must rule them out): linked transactions (s55(1C)), the
higher rates for additional dwellings (Schedule 4ZA, which replaces Table A), the 17% rate (Schedule 4A, taken out of
s55 by s55(1A)), reliefs, and non-residential or mixed land. The code refuses effective dates before 3 December 2014,
for which it holds no rates, and amounts it cannot read. See ambiguities.md.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path

from area import load_rules, rule_periods


@dataclass(frozen=True)
class Slice:
    """One charged row of Table A and the consideration taxed at its rate."""

    lower: Decimal
    upper: Decimal | None
    rate: Decimal
    taxed: Decimal
    tax: Decimal
    text: str
    citation: str


@dataclass(frozen=True)
class Result:
    consideration: Decimal
    effective_date: date
    version: str
    method: str
    version_citation: str
    slices: tuple[Slice, ...]
    unrounded: Decimal
    total: int
    assumptions: tuple[str, ...]


# The same numbering as ambiguities.md, where a reviewer records a decision on each.
ASSUMPTIONS = (
    "A1: the total is rounded down to the whole pound (HMRC's manual SDLTM00050; no statute found).",
    "A2: the effective date given is the transaction's effective date under FA 2003 s119 and s44 (decided by a person).",
    "A3: the land is entirely residential property (FA 2003 s116; decided by a person).",
    "A4: the consideration given is the chargeable consideration (FA 2003 Schedule 4; decided by a person).",
)
SCOPE = "A single purchase, not linked, not at the higher rates and with no relief, in England or Northern Ireland."


def select_version(rules: dict, effective_date: date) -> dict:
    """The one rule version in force on the effective date; anything else is an error, never a guess."""
    found = [version for start, end, version in rule_periods(rules)
             if start <= effective_date and (end is None or effective_date < end)]
    if not found:
        raise ValueError(f"no rule version held for an effective date of {effective_date.isoformat()}")
    if len(found) > 1:
        raise ValueError(f"rule versions overlap on {effective_date.isoformat()}: {[v['id'] for v in found]}")
    return found[0]


def _to_decimal(consideration) -> Decimal:
    if isinstance(consideration, bool) or isinstance(consideration, float):
        raise TypeError("give the consideration as an int, a Decimal or a string, never a float")
    if not isinstance(consideration, (int, Decimal, str)):
        raise TypeError(f"unsupported consideration type: {type(consideration).__name__}")
    try:
        value = Decimal(consideration)
        if not value.is_finite():
            raise ValueError("the consideration must be a finite amount")
        if value < 0:
            raise ValueError("the consideration cannot be negative")
        if value != value.quantize(Decimal("0.01")):
            raise ValueError("the consideration must be in pounds and pence")
    except InvalidOperation:
        raise ValueError(f"cannot read {consideration!r} as an amount in pounds") from None
    return abs(value)  # turns -0 into 0


def compute(consideration, effective_date: date, rules: dict | None = None) -> Result:
    """Tax on a single standard residential transaction, with its trace."""
    value = _to_decimal(consideration)
    if not isinstance(effective_date, date) or isinstance(effective_date, datetime):
        raise TypeError("the effective date must be a datetime.date (a day, not a time)")
    rules = rules if rules is not None else load_rules(Path(__file__).parent)
    version = select_version(rules, effective_date)

    method = version["method"]
    if method not in ("slab", "slice"):
        raise ValueError(f"Unknown charging method: {method}")
    slices = []
    for row, band in enumerate(version["bands"], start=1):
        lower = Decimal(band["lower"])
        upper = Decimal(band["upper"]) if band["upper"] is not None else None
        if value <= lower:
            break
        if method == "slab":
            if upper is not None and value > upper:
                continue
            taxed = value
        else:
            taxed = (value if upper is None else min(value, upper)) - lower
        rate = Decimal(band["rate"])
        slices.append(
            Slice(
                lower=lower,
                upper=upper,
                rate=rate,
                taxed=taxed,
                tax=taxed * rate,
                text=band["text"],
                citation=f"{version['table']}, row {row}",
            )
        )

    unrounded = sum((s.tax for s in slices), Decimal("0"))
    total = int(unrounded.to_integral_value(rounding=ROUND_FLOOR))
    return Result(
        consideration=value,
        effective_date=effective_date,
        version=version["id"],
        method=method,
        version_citation=version["citation"],
        slices=tuple(slices),
        unrounded=unrounded,
        total=total,
        assumptions=ASSUMPTIONS,
    )
