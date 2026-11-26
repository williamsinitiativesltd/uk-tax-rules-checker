"""Discover an area's inputs beside its code, independently of the working directory.

An area's pipeline module exports Area (with source_urls()), inspect(area, rules, read),
compare_model(area, model, declarations, rules, history, read), and
evidence(area, index, rules, history, proof, read, text). History supplies
failure_kinds and finding_labels. The area supplies the checked presentation data.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from importlib import import_module
import json
from pathlib import Path
from types import ModuleType

LEG = "https://www.legislation.gov.uk"
GOV = "https://www.gov.uk"
DAY = timedelta(days=1)


@dataclass
class RuleArea:
    folder: Path
    law: ModuleType


@dataclass
class Area(RuleArea):
    title: str
    section: str
    example: dict
    page: dict
    manual: dict | None = field(default=None, kw_only=True)

    @property
    def sources(self):
        return self.folder / "sources"


@dataclass
class MappedArea(Area):
    act: str
    act_path: str
    provision: str
    provision_path: str
    scope: dict

    @property
    def base(self):
        return LEG + self.act_path


def load_rules(folder):
    return json.loads((folder / "rules.json").read_text(encoding="utf-8"))


def load_area(name):
    folder = Path(__file__).resolve().parent / "areas" / name
    if not name.isidentifier() or not (folder / "area.json").is_file():
        raise ValueError(f"Unknown area: {name}")
    law = import_module(f"areas.{name}.pipeline")
    config = json.loads((folder / "area.json").read_text(encoding="utf-8"))
    return law.Area(folder, law, **config)


def rule_periods(rules):
    periods = []
    for version in rules["versions"]:
        start = date.fromisoformat(version["from"])
        last = date.fromisoformat(version["to"]) if version["to"] else None
        end = last + DAY if last and last < date.max else None
        periods.append((start, end, version))
    return periods
