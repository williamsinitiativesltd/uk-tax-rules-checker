"""Stable encodings for published cases, exported inputs and file fingerprints."""

import csv
import hashlib
import json
import os
from pathlib import Path


def cases_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_inputs(path, cases):
    if path.suffix.lower() == ".json":
        path.write_text(cases_json([{"id": row["id"], "input": row["input"]} for row in cases]), encoding="utf-8")
    elif path.suffix.lower() == ".csv":
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id", *cases[0]["input"]])
            writer.writeheader()
            writer.writerows(dict(id=row["id"], **row["input"]) for row in cases)
    else:
        raise ValueError("Input export requires a .json or .csv extension")


def files_fingerprint(root, paths):
    names = sorted({Path(os.path.relpath(path, root)).as_posix() for path in paths})
    digest = hashlib.sha256()
    sizes = {}
    for name in names:
        data = (root / name).read_bytes()
        sizes[name] = (len(data.splitlines()), len(data))
        # A filename cannot contain NUL, and the byte count delimits arbitrary file contents.
        digest.update(name.encode("utf-8") + b"\0" + len(data).to_bytes(8, "big") + data)
    return digest.hexdigest(), sizes
