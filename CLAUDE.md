# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`timeplus-ocsf-simulator` — an independent Python library that generates simulated OCSF
(Open Cybersecurity Schema Framework) events. Structured to mirror
[`taxi-route-simulator`](https://github.com/timeplus-io/taxi-route-simulator): a slim
`pyproject.toml`, `src/ocsf_simulator/` package, and a stdout-by-default CLI.

## Install and run

```bash
pip install -e .              # editable install (requires modern pip; pip 21 fails)
pip install -e ".[kafka]"     # adds optional Kafka output
pip install -e ".[ocsf]"      # adds real ocsf-lib schema lookup
ocsf-sim --max-events 5       # CLI entry point
python -m ocsf_simulator      # equivalent
python main.py                # example script (4 events)
```

There is no test suite yet. There is no `Makefile`, `tox.ini`, or CI.

## Hard rules

- **stdout is reserved for the JSON event stream.** Every event the simulator emits is one
  JSON object per line on stdout. Logging, warnings, schema-load chatter, and `print()`
  diagnostics MUST go to stderr. `JSONSchemaFaker` already does this — preserve the pattern
  in any new code. If you need to add user-facing output, route it to stderr or to the
  `logging` module (which is already configured to stderr in `simulator.py`).

- **Do not reintroduce Timeplus / proton-driver output.** The library was deliberately
  migrated from a Timeplus-coupled version into an independent lib. `TimeplusClient`,
  `proton-driver`, and the old `tp-sync/` SQL were dropped on purpose. Kafka remains as an
  optional extra because it isn't Timeplus-specific.

- **Optional dependencies are loaded via `try/except ImportError`** (see `simulator.py`
  for `kafka`, `json_schema_faker.py` for `ocsf`). Don't move `kafka-python` or `ocsf-lib`
  into base `dependencies` in `pyproject.toml` — they belong under
  `[project.optional-dependencies]`.

- **Package data lives inside the package and is loaded via `importlib.resources`.**
  See `geonames.py` — it loads `data/worldcities.csv` from
  `resources.files(__package__).joinpath(...)`, not a relative path. Relative paths break
  once the package is pip-installed. Any new data file goes under
  `src/ocsf_simulator/data/` and gets added to `[tool.setuptools.package-data]` in
  `pyproject.toml` and `MANIFEST.in`.

## Layout

```
src/ocsf_simulator/
  __init__.py           public API exports
  __main__.py           enables `python -m ocsf_simulator`
  simulator.py          OCSFEventSimulator, SimulatorConfig, Stdout/Kafka clients, main_cli
  json_schema_faker.py  event generator (1276 lines, copied verbatim from the migration source)
  geonames.py           random city lookup; uses importlib.resources
  data/worldcities.csv  package data
```

`main_cli` (in `simulator.py`) is the `ocsf-sim` entry point declared in `pyproject.toml`.
`stream_ocsf_events` is the library-API generator for programmatic use.
