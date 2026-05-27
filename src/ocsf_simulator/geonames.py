"""Random city lookup, used to give events realistic location data."""
import csv
import random
from functools import lru_cache
from importlib import resources
from typing import Dict, List


@lru_cache(maxsize=1)
def _load_cities() -> List[Dict[str, object]]:
    cities: List[Dict[str, object]] = []
    with resources.files(__package__).joinpath("data/worldcities.csv").open(
        "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cities.append(
                    {
                        "name": row["name"],
                        "country": row["country_code"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                    }
                )
            except (KeyError, ValueError):
                continue
    return cities


def get_random_city() -> Dict[str, object]:
    cities = _load_cities()
    if not cities:
        return {"name": "Unknown", "country": "??", "latitude": 0.0, "longitude": 0.0}
    return random.choice(cities)
