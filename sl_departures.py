import requests
import json
import pandas as pd
import os
from datetime import datetime

# SL RealTime Departures 4 API endpoint
# https://www.trafiklab.se/api/our-apis/sl/transport/#/default/Departures

# Delay = scheduled time - expected time

BASE_URL = "https://transport.integration.sl.se/v1/sites/{siteId}/departures"

SITE_IDS = [
    7981,  # Arninge
    9600,  # Stockholms östra
    9200,  # Mörby centrum
    9638,  # Mörby station
    9201,  # Danderyds sjukhus
    9633,  # Roslags Näsby
    2200,  # Roslags Näsby trafikplats
]

# TODO: add bus lines
LINES = [28]

MODES = [
    "BUS",
    "TRAM",  # Roslagsbanan is designated as a tram
]


def fetch_departures(
    site_id: int, lines: list[int] | None = None, modes: list[str] | None = None
):
    response = requests.get(BASE_URL.format(siteId=site_id))
    response.raise_for_status()

    raw = response.json()

    filtered = {"departures": []}

    for departure in raw.get("departures", []):
        if lines and departure["line"]["id"] not in lines:
            continue

        if modes and departure["line"]["transport_mode"] not in modes:
            continue

        filtered["departures"].append(departure)

    return filtered


rows = []
for site_id in SITE_IDS:
    data = fetch_departures(site_id=site_id, lines=LINES, modes=MODES)
    with open(f"departures_{site_id}.json", "w") as f:
        json.dump(data, f, indent=2)

    for dep in data["departures"]:
        line_id = dep["line"]["id"]
        transport_mode = dep["line"]["transport_mode"]
        destination = dep["destination"]
        scheduled_time = dep.get("scheduled")
        expected_time = dep.get("expected")
        # Parse times and calculate delay in seconds (if both times exist)
        delay = None
        if scheduled_time and expected_time:
            try:
                t1 = datetime.fromisoformat(scheduled_time)
                t2 = datetime.fromisoformat(expected_time)
                delay = (t2 - t1).total_seconds()
            except Exception:
                delay = None
        rows.append(
            {
                "site_id": site_id,
                "line_id": line_id,
                "transport_mode": transport_mode,
                "scheduled_time": scheduled_time,
                "expected_time": expected_time,
                "delay": delay,
                "destination": destination,
            }
        )

    # Create DataFrame and append to CSV
    csv_file = f"departures_{site_id}.csv"

    df = pd.DataFrame(rows)
    if os.path.exists(csv_file):
        df.to_csv(csv_file, mode="a", header=False, index=False)
    else:
        df.to_csv(csv_file, mode="w", header=True, index=False)
