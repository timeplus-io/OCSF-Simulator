# OCSF Simulator

A Python library and CLI that generates simulated [OCSF](https://schema.ocsf.io/)
(Open Cybersecurity Schema Framework) event streams. Useful for testing
streaming pipelines, security analytics tools, SIEMs, and detection rules with
realistic synthetic data.

## Install

```bash
pip install timeplus-ocsf-simulator
```

Optional extras:

```bash
pip install "timeplus-ocsf-simulator[ocsf]"    # use the real ocsf-lib schema
pip install "timeplus-ocsf-simulator[kafka]"   # enable Kafka output
pip install "timeplus-ocsf-simulator[all]"
```

Or install from source:

```bash
git clone https://github.com/timeplus-io/OCSF-Simulator.git
cd OCSF-Simulator
pip install -e .
```

## Use as a CLI

By default, events are written as JSON lines to stdout:

```bash
ocsf-sim --interval 1.0 --batch-size 5 --max-events 20
```

Send events to Kafka instead:

```bash
ocsf-sim --enable-kafka --kafka-servers localhost:9092 --kafka-topic ocsf-events
```

Common flags:

| Flag | Description |
| --- | --- |
| `--interval` | Seconds between batches (default `1.0`) |
| `--batch-size` | Events per batch (default `10`) |
| `--max-events` | Stop after generating N events |
| `--duration` | Stop after N minutes |
| `--event-classes` | OCSF class UIDs to generate (default `3002 4001 1007 2001`) |
| `--profiles` | OCSF profiles to apply (default `cloud security_control`) |
| `--ocsf-version` | OCSF schema version (default `1.1.0`) |
| `--enable-kafka` | Publish events to Kafka |

Run `ocsf-sim --help` for the full list.

## Use as a library

```python
from ocsf_simulator import JSONSchemaFaker, stream_ocsf_events

# One-shot event generation
faker = JSONSchemaFaker(ocsf_version="1.1.0")
event = faker.generate_ocsf_event(3002, profiles=["host", "security_control"])

# Streaming generator (yields events forever)
for event in stream_ocsf_events(event_classes=[3002, 4001], interval=1.0):
    print(event)
```

## Supported event classes

The simulator can generate events for any OCSF class, with richer dedicated
generators for these commonly-used ones:

| UID | Class |
| --- | --- |
| 1001 | File System Activity |
| 1007 | Process Activity |
| 2001 | Security Finding |
| 3002 | Authentication |
| 4001 | Network Activity |

## License

Apache-2.0
