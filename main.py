"""Example: print a few simulated OCSF events to stdout."""
import json

from ocsf_simulator import JSONSchemaFaker


def main():
    faker = JSONSchemaFaker(ocsf_version="1.1.0")
    for class_uid in [3002, 4001, 1007, 2001]:
        event = faker.generate_ocsf_event(class_uid, profiles=["cloud", "security_control"])
        print(json.dumps(event, default=str))


if __name__ == "__main__":
    main()
