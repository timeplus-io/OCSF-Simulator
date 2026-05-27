"""OCSF Event Simulator.

Generates realistic OCSF (Open Cybersecurity Schema Framework) events for
testing streaming pipelines, SIEMs, and detection rules.
"""

__version__ = "0.1.0"

from .json_schema_faker import JSONSchemaFaker
from .simulator import (
    EventMetrics,
    KafkaClient,
    OCSFEventSimulator,
    SimulatorConfig,
    StdoutClient,
    main_cli,
    stream_ocsf_events,
)

__all__ = [
    "JSONSchemaFaker",
    "OCSFEventSimulator",
    "SimulatorConfig",
    "EventMetrics",
    "StdoutClient",
    "KafkaClient",
    "stream_ocsf_events",
    "main_cli",
]
