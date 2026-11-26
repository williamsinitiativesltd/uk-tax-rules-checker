"""Compare supplier answers with the published cases and the reference calculator."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from html import escape
from http.client import HTTPException
from itertools import islice
import json
import math
from pathlib import Path
import random
import shlex
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from checker_formats import cases_json, files_fingerprint, write_inputs
from checker_inputs import load_inputs
from presentation import document, table

DEFAULT_SAMPLES = 2000
DEFAULT_SEED = 20261126
# Every report carries this, and the pack's pages show it. It lives here so the supplier kit needs no content folder.
SCOPE = ("Each expected answer comes from the prototype's calculator. The build checks that calculator against the "
         "Acts, and against every figure in the mathematical proofs; if any check fails, nothing is published. A pass "
         "means your program gave the expected answer for every case and every extra input the checker tried. It does "
         "not prove your program is right for inputs nobody tried: that would need your program itself to be written "
         "in, or checked by, a proof checker.")


class VendorError(ValueError):
    def __init__(self, reason, actual=None):
        super().__init__(reason)
        self.actual = actual


def vendor_call(command, inputs, output, timeout):
    try:
        proc = subprocess.run(command, input=json.dumps(inputs).encode(), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise VendorError(f"timed out after {timeout:g} s") from exc
    except OSError as exc:
        raise VendorError(f"could not start command: {exc}") from exc
    if proc.returncode:
        raise VendorError(f"exit {proc.returncode}: {proc.stderr.decode(errors='replace').strip()}",
                          proc.stdout.decode(errors="replace"))

    return decode_reply(proc.stdout, output)


def decode_reply(data, output):
    try:
        answer = json.loads(data.decode("utf-8"), parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise VendorError("invalid JSON", data.decode(errors="replace")) from exc
    return checked_answer(answer, output, data.decode(errors="replace"))


def invalid_constant(token):
    raise ValueError(token)


def checked_answer(answer, output, raw):
    if not isinstance(answer, dict) or answer.keys() != {output} or type(answer[output]) is not int:
        raise VendorError(f"expected one object with integer field {output}", raw)
    return answer[output]


def post_input(url, inputs, output, timeout):
    request = Request(url, data=json.dumps(inputs).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as reply:
            return decode_reply(reply.read(), output)
    except HTTPError as exc:
        with exc:
            raise VendorError(f"HTTP {exc.code}: {exc.reason}", exc.read().decode(errors="replace")) from exc
    except (TimeoutError, URLError, HTTPException, OSError) as exc:
        if isinstance(getattr(exc, "reason", exc), TimeoutError):
            raise VendorError(f"timed out after {timeout:g} s") from exc
        raise VendorError(f"HTTP request failed: {exc}") from exc


def read_answers(path, cases):
    def unique_fields(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"Duplicate answers file key: {key}")
            obj[key] = value
        return obj

    data = path.read_bytes()
    replies = json.loads(data.decode("utf-8"), object_pairs_hook=unique_fields, parse_constant=invalid_constant)
    if not isinstance(replies, dict):
        raise ValueError("Expected a JSON object keyed by case ID")
    unexpected = replies.keys() - {row["id"] for row in cases}
    if unexpected:
        raise ValueError(f"Unexpected case ID: {min(unexpected)}")
    return replies, sha256(data).hexdigest()


def code_fingerprint(command, code):
    if not code:
        executable = Path(command[0])
        if not executable.is_file():
            return None
        code = [executable]
    files = []
    for path in map(Path, code):
        if path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file())
        elif path.is_file():
            files.append(path)
        else:
            raise ValueError(f"Code path is not a file or directory: {path}")
    if not files:
        raise ValueError("No files in the specified code paths")
    return files_fingerprint(Path.cwd(), files)[0]


def input_set(area, rules, suite, samples, seed):
    sampled = area.law.conformance.sample(rules, random.Random(seed))
    return [*suite["cases"], *(dict(id=f"Sample {i}", **row)
                               for i, row in enumerate(islice(sampled, samples), 1))]


def run(area, rules, suite, command, samples, seed, timeout, workers=1, *, code=(), answers=None, url=None):
    adapter = area.law.conformance
    version = sha256((area.folder / "rules.json").read_bytes() + cases_json(suite).encode("utf-8")
                     + (area.folder / "lean/checked.json").read_bytes()).hexdigest()
    run_cases = input_set(area, rules, suite, samples, seed)
    fingerprint = sha256(cases_json([(r["input"], r["expected"]) for r in run_cases]).encode("utf-8")).hexdigest()
    report = dict(area=area.folder.name, suite_version=version, seed=seed, published=len(suite["cases"]),
                  differential=samples, full_check=seed == DEFAULT_SEED and samples == DEFAULT_SAMPLES,
                  case_fingerprint=fingerprint, code_fingerprint=None,
                  scope=SCOPE, failures=[])

    if answers is not None:
        replies, report["answers_sha256"] = read_answers(answers, run_cases)
        report["provenance"] = "A file of answers shows nothing about which code produced them."
        report["scope"] = "A pass means the supplied answers match the reference answers for the tested cases."

        def get_answer(row):
            if row["id"] not in replies:
                raise VendorError("missing answer")
            reply = replies[row["id"]]
            return checked_answer(reply, adapter.OUTPUT, reply)
    elif url is not None:
        endpoint = urlsplit(url)
        if endpoint.scheme not in ("http", "https") or not endpoint.hostname:
            raise ValueError("Expected an HTTP or HTTPS endpoint URL")
        report["url"] = url

        def get_answer(row):
            return post_input(url, row["input"], adapter.OUTPUT, timeout)
    else:
        report["code_fingerprint"] = code_fingerprint(command, code)

        def get_answer(row):
            return vendor_call(command, row["input"], adapter.OUTPUT, timeout)

    def failure(row):
        try:
            actual = {adapter.OUTPUT: get_answer(row)}
            if actual == row["expected"]:
                return None
            reason = "result differs"
        except VendorError as error:
            actual, reason = error.actual, str(error)
        return dict(case=row["id"], input=row["input"],
                    expected=row["expected"], actual=actual, reason=reason, provision=row["provision"])

    with ThreadPoolExecutor(workers) as pool:
        report["failures"] = [f for f in pool.map(failure, run_cases) if f]
    return report


def summary(report):
    failures = report["failures"]
    check = ("Full published check." if report["full_check"] else
             f"Not the full published check: {report['differential']} generated inputs with seed {report['seed']}. "
             f"The full check uses {DEFAULT_SAMPLES} with seed {DEFAULT_SEED}. Use this run for testing only.")
    lines = [f"{'FAIL' if failures else 'PASS'} {report['area']}: {report['published']} published cases, "
             f"{report['differential']} extra inputs, {len(failures)} failed (seed {report['seed']})",
             check,
             "Case set fingerprint (SHA-256): " + report["case_fingerprint"]]
    if "answers_sha256" in report:
        lines.extend([report["provenance"], "Answers file SHA-256: " + report["answers_sha256"]])
    if "url" in report:
        lines.append("Supplier URL: " + report["url"])
    if report["code_fingerprint"] is None:
        lines.append("No code fingerprint was recorded.")
    else:
        lines.append(f"This result applies to the code with fingerprint {report['code_fingerprint']}.")
    if failures:
        f = failures[0]
        reason = f["reason"]
        lines.append(f"First failure, case {f['case']}: {json.dumps(f['input'])}\n"
                     f"Expected {json.dumps(f['expected'])}, actual {json.dumps(f['actual'])}. "
                     f"{reason[:1].upper()}{reason[1:]}. {f['provision']}")
    return "\n".join(lines)


def write_report(path, report):
    path.with_suffix(".json").write_text(cases_json(report), encoding="utf-8")
    body = "<pre>" + escape(summary(report)) + "</pre>"
    if report["failures"]:
        keys = ("case", "input", "expected", "actual", "reason", "provision")
        body += table(("Case", "Input", "Expected", "Actual", "Reason", "Provision"),
                      ([f[key] for key in keys] for f in report["failures"]))
    html = document("Conformance report", body, escape(report["scope"]), {}, description=report["scope"].split(". ")[0] + ".")
    path.with_suffix(".html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export-inputs", type=Path, help="write the full input set as JSON or CSV and exit")
    mode.add_argument("--answers", type=Path, help="compare a JSON object of replies keyed by case ID")
    mode.add_argument("--url", help="POST each input to this HTTP endpoint")
    mode.add_argument("--cmd", help="vendor executable and arguments, shell quoting accepted")
    parser.add_argument("--code", type=Path, action="append", help="fingerprint this file or directory (repeatable)")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout", type=float, default=5, help="seconds per call")
    parser.add_argument("--report", type=Path, help="JSON report path, also writes its HTML sibling")
    args = parser.parse_args()
    if args.samples < 0 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("samples must be non-negative and timeout must be positive and finite")
    try:
        if args.code and args.cmd is None:
            parser.error("--code requires --cmd")
        command = shlex.split(args.cmd) if args.cmd is not None else None
        if command == []:
            parser.error("empty vendor command")
        area, rules, suite = load_inputs(args.area)
        if args.export_inputs:
            write_inputs(args.export_inputs, input_set(area, rules, suite, args.samples, args.seed))
            return 0
        report = run(area, rules, suite, command, args.samples, args.seed,
                     args.timeout, code=args.code, answers=args.answers, url=args.url)
        print(summary(report))
        write_report(args.report or Path(f"{area.folder.name}-conformance.json"), report)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Conformance check failed: {exc}\n")
    return int(bool(report["failures"]))


if __name__ == "__main__":
    sys.exit(main())
