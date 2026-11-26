# UK tax rules checker

Check tax software against published test cases for two UK tax rules: the
income tax personal allowance (Income Tax Act 2007 s35) and the standard
residential rates of Stamp Duty Land Tax. Every expected answer cites the
provision it rests on.

This is a prototype by Williams Initiatives Ltd. It is not HMRC software and
not tax advice, and the cases have not yet been reviewed by a tax professional.

## What is here

- `conformance.py`: the checker. It runs your software on every published case
  and on generated inputs, many at or one pound either side of a band boundary,
  and reports each difference with its provision.
- `areas/*/calculator.py` and `ts/`: reference calculators in Python and
  TypeScript, both reading the dated rule data in `areas/*/rules.json`.
- `*-cases.json` and the JSON schemas: the published cases and the request and
  reply formats.
- `areas/*/lean/`: the proof model of each rule and the record of its check.
- `vendors/`: for each rule, a correct example program and one with a
  deliberate mistake.

See LICENSE: MIT for the code, the Open Government Licence for the rule data
and cases.

## Run it

Keep the directory layout. From this directory, use Python 3.10 or later with
its standard library. Try both correct programs:

```sh
python3 -I conformance.py personal_allowance --cmd "python3 -I vendors/pa_correct.py" --code vendors/pa_correct.py --samples 12 --report pa.json
python3 -I conformance.py sdlt --cmd "python3 -I vendors/sdlt_correct.py" --code vendors/sdlt_correct.py --samples 12 --report sdlt.json
```

`--samples 12` keeps this first try quick: it adds 12 generated inputs to the
published cases. Leave it out for the full check, which adds 2,000. Replace
both occurrences of `_correct.py` with `_buggy.py` to see a failure.
For your own program, pass its command to `--cmd` and the files that do the
calculation to `--code`: the report then records their fingerprint, so it says
which code passed. The checker sends one JSON request per process and expects
one JSON reply. A pass exits 0. A mismatch exits 1 and appears in both the JSON
report and the HTML report beside it.

Two other ways to connect:

- `--url URL` sends each input as JSON to your web service.
- `--export-inputs inputs.json` writes every input for a seed, and
  `--answers answers.json` compares your answers. A file of answers shows
  nothing about which code produced it, and the report says so.

To recheck the proofs and build both model executables, use Lake with each
area's pinned Lean toolchain:

```sh
(cd areas/personal_allowance/lean && lake build)
(cd areas/sdlt/lean && lake build)
```

## Fingerprint

Kit fingerprint (SHA-256): `a63952fbac4663d7f485ef8230dd97d272acf3f2b8fffd7149564040f01040cc`

The fingerprint covers every supplied file except this README, which contains
the digest. In sorted relative path order, hash each UTF-8 path with forward
slashes, a zero byte, its eight-byte big-endian file size and the file bytes.
