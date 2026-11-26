"""Read the cases verified and exported by the pack build."""

from importlib import import_module
import json
from pathlib import Path

from area import RuleArea, load_rules


def load_inputs(name):
    root = Path(__file__).resolve().parent
    folder = root / "areas" / name
    if not name.isidentifier() or not (folder / "rules.json").is_file():
        raise ValueError(f"Unknown area: {name}")
    suite = json.loads((folder / "cases.json").read_text(encoding="utf-8"))
    return RuleArea(folder, import_module(f"areas.{name}")), load_rules(folder), suite
