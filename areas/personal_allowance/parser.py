"""Read the specific CLML clauses that supply the s35 amount, taper and tax bands."""

from dataclasses import dataclass
import gzip
import json
import re

from legislation import words


def filename(stem):
    return f"legislation/{stem}.xml"


def source_reader(sources, read):
    return lambda stem: read(sources / filename(stem))


def clause(root, address):
    node = root.find(f".//*[@id='{address}']")
    if node is None:
        raise ValueError(f"Missing provision {address}")
    return node


def amount(text):
    matches = re.findall(r"£\s*(\d+(?:[,.]\d+)*)", text)
    if len(matches) != 1 or not re.fullmatch(r"\d+|\d{1,3}(?:,\d{3})+", matches[0]):
        raise ValueError(f"Expected one statutory sum in {text}")
    return int(matches[0].replace(",", ""))


def years(text):
    result = set()
    for first, last in re.findall(r"\b(\d{4})-(\d{4}|\d{2})\b", text):
        if int(last) % 100 != (int(first) + 1) % 100:
            raise ValueError(f"Invalid tax year {first}-{last}")
        result.add(int(first))
    return result


def year_label(year):
    return f"{year}-{(year + 1) % 100:02d}"


@dataclass
class Provision:
    act: str
    section: str
    first: str | None
    last: str | None

    @classmethod
    def parse(cls, citation):
        match = re.fullmatch(r"([A-Z]+ \d{4}) s(\d+)(?:\((\d+)\)(?:-\((\d+)\))?)?", citation)
        if not match:
            raise ValueError(f"Cannot read provision: {citation}")
        return cls(*match.groups())

    def text(self, xml, paragraph=None):
        stem = self.act.lower().replace(" ", "") + "-s" + self.section
        address = "section-" + self.section
        if suffix := paragraph or self.first:
            address += "-" + suffix
        return words(clause(xml(stem), address))


def tax_bands(xml, rules):
    tax = rules["tax"]

    def provision(key, paragraph=None):
        return Provision.parse(tax[key]).text(xml, paragraph)

    rates = []
    section = provision("rates")
    if years(section) != {2026}:
        raise ValueError(f"{tax['rates']} rates must apply to 2026-27")
    for name in ("basic", "higher", "additional"):
        match = re.search(rf"the {name} rate is (\d+)%", section)
        if not match:
            raise ValueError(f"Missing {name} rate in {tax['rates']}")
        rates.append(int(match[1]))

    basic = amount(provision("bands", "5"))
    fixed_basic = provision("basic_limit")
    fixed_higher = provision("higher_limit", "4")
    formula = provision("bands", "5A")
    for term in ("twice the amount specified in subsection (1) of section 35", "plus",
                 "the amount specified in subsection (2) of that section"):
        if term not in formula:
            raise ValueError("Unrecognised ITA s10(5A) higher rate limit")
    higher = 2 * rules["years"]["2026"]["amount"] + rules["taper"]["income_limit"]
    if (2026 not in years(fixed_basic) or basic != amount(fixed_basic)
            or basic != tax["basic_limit_pounds"] or 2026 not in years(fixed_higher) or higher != amount(fixed_higher)):
        raise ValueError("2026-27 limits in ITA s10 and the Finance Acts disagree")
    return list(zip((basic, higher, None), rates))


def check_taper(xml, taper):
    provision = Provision.parse(taper["citation"])
    reduction = provision.text(xml, provision.first)
    rounding = provision.text(xml, provision.last)
    effect = Provision.parse(taper["commencement"]).text(xml)
    if ("adjusted net income exceeds" not in reduction or "one-half of the excess" not in reduction
            or "rounded up to the nearest amount which is a multiple of £1" not in rounding
            or "subsequent tax years" not in effect):
        raise ValueError("Unrecognised statutory taper or rounding rule")
    first, = years(effect)
    if (taper["first_year"], taper["income_limit"], taper["divisor"], taper["rounding"]) != (
            first, amount(reduction), 2, "remaining allowance up to a whole pound"):
        raise ValueError(f"Coded taper differs from {taper['citation']} or {taper['commencement']}")


def check_part3(xml):
    part = xml("ita2007-part3")
    for section in ("35", "58"):
        address = "section-" + section
        stem = "ita2007-s" + section
        if words(clause(part, address)) != words(clause(xml(stem), address)):
            raise ValueError(f"ita2007-part3 and {stem} disagree on section {section}")


def check_guidance(path, taper):
    with gzip.open(path, "rt", encoding="utf-8") as lines:
        page, = (json.loads(line) for line in lines)
    threshold = re.search(r"Personal Allowance</a>[^<]*adjusted net income over ([^<(]+)", page["body"])
    if not threshold or amount(threshold[1]) != taper["income_limit"]:
        raise ValueError("Adjusted net income guidance disagrees with the taper threshold")
