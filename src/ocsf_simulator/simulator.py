"""OCSF Event Simulator.

Generates realistic OCSF events and emits them either to stdout (JSON lines,
the default) or to a Kafka topic.
"""
import argparse
import json
import logging
import random
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from .json_schema_faker import JSONSchemaFaker

try:
    from kafka import KafkaProducer  # type: ignore
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False


@dataclass
class SimulatorConfig:
    """Configuration for the OCSF Event Simulator."""

    interval_seconds: float = 1.0
    batch_size: int = 10
    max_events: Optional[int] = None
    duration_minutes: Optional[int] = None

    ocsf_version: str = "1.1.0"
    event_classes: List[int] = field(
        default_factory=lambda: [3002, 4001, 1007, 2001]
    )
    profiles: List[str] = field(default_factory=lambda: ["cloud", "security_control"])

    stdout_enabled: bool = True

    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "ocsf-events"
    kafka_key_field: Optional[str] = "metadata.uid"

    log_level: str = "INFO"
    log_file: Optional[str] = None

    max_workers: int = 4


class EventMetrics:
    """Track simulator metrics."""

    def __init__(self):
        self.events_generated = 0
        self.events_sent_stdout = 0
        self.events_sent_kafka = 0
        self.kafka_errors = 0
        self.start_time = datetime.now()
        self.last_report_time = datetime.now()
        self._lock = threading.Lock()

    def increment_generated(self, count: int = 1):
        with self._lock:
            self.events_generated += count

    def increment_stdout(self, count: int = 1):
        with self._lock:
            self.events_sent_stdout += count

    def increment_kafka_sent(self, count: int = 1):
        with self._lock:
            self.events_sent_kafka += count

    def increment_kafka_errors(self, count: int = 1):
        with self._lock:
            self.kafka_errors += count

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            eps = self.events_generated / runtime if runtime > 0 else 0
            return {
                "runtime_seconds": runtime,
                "events_generated": self.events_generated,
                "events_sent_stdout": self.events_sent_stdout,
                "events_sent_kafka": self.events_sent_kafka,
                "kafka_errors": self.kafka_errors,
                "events_per_second": round(eps, 2),
            }

    def should_report(self, interval_seconds: int = 30) -> bool:
        now = datetime.now()
        if (now - self.last_report_time).total_seconds() >= interval_seconds:
            self.last_report_time = now
            return True
        return False


class StdoutClient:
    """Writes events as JSON lines to stdout."""

    def __init__(self, config: SimulatorConfig):
        self.config = config

    def send_events(self, events: List[Dict[str, Any]], metrics: EventMetrics):
        for event in events:
            sys.stdout.write(json.dumps(event, default=str) + "\n")
        sys.stdout.flush()
        metrics.increment_stdout(len(events))


class KafkaClient:
    """Kafka producer client for OCSF events."""

    def __init__(self, config: SimulatorConfig):
        if not KAFKA_AVAILABLE:
            raise ImportError(
                "kafka-python not installed. Install with: pip install 'timeplus-ocsf-simulator[kafka]'"
            )
        self.config = config
        self.producer: Optional[Any] = None
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8") if k else None,
                acks="all",
                retries=3,
                max_in_flight_requests_per_connection=1,
                enable_idempotence=True,
                linger_ms=5,
                request_timeout_ms=30000,
            )
            self.logger.info(
                "Connected to Kafka: %s", self.config.kafka_bootstrap_servers
            )
            return True
        except Exception as e:
            self.logger.error("Failed to connect to Kafka: %s", e)
            return False

    def send_events(self, events: List[Dict[str, Any]], metrics: EventMetrics):
        if not self.producer:
            metrics.increment_kafka_errors(len(events))
            return
        for event in events:
            try:
                key = None
                if self.config.kafka_key_field:
                    key = self._get_nested_value(event, self.config.kafka_key_field)
                self.producer.send(self.config.kafka_topic, value=event, key=key)
                metrics.increment_kafka_sent()
            except Exception as e:
                self.logger.error("Failed to send event to Kafka: %s", e)
                metrics.increment_kafka_errors()
        try:
            self.producer.flush(timeout=5)
        except Exception as e:
            self.logger.error("Failed to flush Kafka producer: %s", e)

    @staticmethod
    def _get_nested_value(obj: Dict[str, Any], path: str) -> Any:
        for key in path.split("."):
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                return None
        return obj

    def close(self):
        if self.producer:
            try:
                self.producer.close(timeout=10)
            except Exception as e:
                self.logger.error("Error closing Kafka producer: %s", e)


class OCSFEventSimulator:
    """Main OCSF event simulator."""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.running = False
        self.logger = self._setup_logging()
        self.metrics = EventMetrics()
        self.faker = JSONSchemaFaker(ocsf_version=config.ocsf_version)
        self.stdout_client: Optional[StdoutClient] = None
        self.kafka_client: Optional[KafkaClient] = None
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("ocsf_simulator")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        if not logger.handlers:
            fmt = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            # Log to stderr so it doesn't pollute the JSON event stream on stdout.
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(fmt)
            logger.addHandler(handler)
            if self.config.log_file:
                fh = logging.FileHandler(self.config.log_file)
                fh.setFormatter(fmt)
                logger.addHandler(fh)
        return logger

    def _signal_handler(self, signum, frame):
        self.logger.info("Received signal %s, shutting down...", signum)
        self.running = False

    def _connect_clients(self) -> bool:
        if self.config.stdout_enabled:
            self.stdout_client = StdoutClient(self.config)
        if self.config.kafka_enabled:
            if not KAFKA_AVAILABLE:
                self.logger.error(
                    "Kafka enabled but kafka-python not installed"
                )
                return False
            self.kafka_client = KafkaClient(self.config)
            if not self.kafka_client.connect():
                return False
        if not (self.config.stdout_enabled or self.config.kafka_enabled):
            self.logger.error("No output targets enabled")
            return False
        return True

    def _generate_events(self) -> List[Dict[str, Any]]:
        events = []
        for _ in range(self.config.batch_size):
            class_uid = random.choice(self.config.event_classes)
            event = self.faker.generate_ocsf_event(
                class_uid, profiles=self.config.profiles
            )
            event["_simulator"] = {
                "generated_at": datetime.now().isoformat(),
                "class_uid": class_uid,
                "profiles": self.config.profiles,
                "version": self.config.ocsf_version,
            }
            events.append(event)
        self.metrics.increment_generated(len(events))
        return events

    def _send_events(self, events: List[Dict[str, Any]]):
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            if self.stdout_client:
                futures.append(
                    executor.submit(self.stdout_client.send_events, events, self.metrics)
                )
            if self.kafka_client:
                futures.append(
                    executor.submit(self.kafka_client.send_events, events, self.metrics)
                )
            for future in futures:
                try:
                    future.result(timeout=30)
                except Exception as e:
                    self.logger.error("Error sending events: %s", e)

    def _should_stop(self) -> bool:
        if (
            self.config.max_events
            and self.metrics.events_generated >= self.config.max_events
        ):
            return True
        if self.config.duration_minutes:
            mins = (datetime.now() - self.metrics.start_time).total_seconds() / 60
            if mins >= self.config.duration_minutes:
                return True
        return False

    def _report_metrics(self):
        stats = self.metrics.get_stats()
        self.logger.info(
            "Metrics - Generated: %s, Stdout: %s, Kafka: %s, Rate: %s ev/s, Kafka errors: %s",
            stats["events_generated"],
            stats["events_sent_stdout"],
            stats["events_sent_kafka"],
            stats["events_per_second"],
            stats["kafka_errors"],
        )

    def run(self) -> bool:
        self.logger.info("Starting OCSF Event Simulator")
        if not self._connect_clients():
            return False
        self.running = True
        try:
            while self.running and not self._should_stop():
                start = time.time()
                events = self._generate_events()
                self._send_events(events)
                if self.metrics.should_report():
                    self._report_metrics()
                elapsed = time.time() - start
                sleep_time = max(0, self.config.interval_seconds - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            self._cleanup()
        self._report_metrics()
        self.logger.info("Simulator stopped")
        return True

    def _cleanup(self):
        if self.kafka_client:
            self.kafka_client.close()


def stream_ocsf_events(
    event_classes: Optional[List[int]] = None,
    profiles: Optional[List[str]] = None,
    ocsf_version: str = "1.1.0",
    interval: float = 0.0,
    max_events: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield simulated OCSF events as Python dicts.

    Args:
        event_classes: OCSF class UIDs to draw from (random pick per event).
            Defaults to [3002, 4001, 1007, 2001].
        profiles: OCSF profiles to apply. Defaults to ['cloud', 'security_control'].
        ocsf_version: OCSF schema version.
        interval: Seconds to sleep between events (0 = as fast as possible).
        max_events: Stop after this many events (None = infinite).
    """
    classes = event_classes or [3002, 4001, 1007, 2001]
    profs = profiles or ["cloud", "security_control"]
    faker = JSONSchemaFaker(ocsf_version=ocsf_version)
    n = 0
    while max_events is None or n < max_events:
        class_uid = random.choice(classes)
        event = faker.generate_ocsf_event(class_uid, profiles=profs)
        event["_simulator"] = {
            "generated_at": datetime.now().isoformat(),
            "class_uid": class_uid,
            "profiles": profs,
            "version": ocsf_version,
        }
        yield event
        n += 1
        if interval > 0:
            time.sleep(interval)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OCSF Event Simulator")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--duration", type=int, help="Stop after N minutes")
    parser.add_argument("--ocsf-version", default="1.1.0")
    parser.add_argument(
        "--event-classes",
        nargs="+",
        type=int,
        default=[3002, 4001, 1007, 2001],
    )
    parser.add_argument(
        "--profiles", nargs="+", default=["cloud", "security_control"]
    )
    parser.add_argument(
        "--no-stdout",
        action="store_true",
        help="Disable stdout JSON output",
    )
    parser.add_argument("--enable-kafka", action="store_true")
    parser.add_argument("--kafka-servers", default="localhost:9092")
    parser.add_argument("--kafka-topic", default="ocsf-events")
    parser.add_argument("--kafka-key-field", default="metadata.uid")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument("--log-file")
    parser.add_argument("--max-workers", type=int, default=4)
    return parser


def main_cli():
    parser = _build_arg_parser()
    args = parser.parse_args()

    config = SimulatorConfig(
        interval_seconds=args.interval,
        batch_size=args.batch_size,
        max_events=args.max_events,
        duration_minutes=args.duration,
        ocsf_version=args.ocsf_version,
        event_classes=args.event_classes,
        profiles=args.profiles,
        stdout_enabled=not args.no_stdout,
        kafka_enabled=args.enable_kafka,
        kafka_bootstrap_servers=args.kafka_servers,
        kafka_topic=args.kafka_topic,
        kafka_key_field=args.kafka_key_field,
        log_level=args.log_level,
        log_file=args.log_file,
        max_workers=args.max_workers,
    )

    try:
        simulator = OCSFEventSimulator(config)
        success = simulator.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main_cli()
