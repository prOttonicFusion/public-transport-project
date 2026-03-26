import requests
import json
import pandas as pd
import os
from datetime import datetime
import time

# SL RealTime Departures 4 API endpoint
# https://www.trafiklab.se/api/our-apis/sl/transport/#/default/Departures

# Delay = scheduled time - expected time

BASE_URL = "https://transport.integration.sl.se/v1/sites/{siteId}/departures"

SITE_IDS = {
    7981: "Arninge",
    9600: "Stockholms_östra",
    9200: "Mörby_centrum",
    9638: "Mörby_station",
    9201: "Danderyds_sjukhus",
    9633: "Roslags_Näsby",
    2200: "Roslags_Näsby_trafikplats",
}

# Roslagsbanan stations
ROSLAGSBANAN_SITE_IDS = {
    7982: "Arninge_station",  # stop_areas: 7035, 61060
    9666: "Hägernäs",  # stop_areas: 7031, 61748
    9667: "Viggbyholm",  # stop_areas: 7021, 61717, 17456
    9668: "Galoppfältet",  # stop_areas: 7011, 61503
    9669: "Täby_centrum",  # stop_areas: 7001, 17452, 61011
    9633: "Roslags_Näsby",  # stop_areas: 7191, 17418, 60237
    9634: "Enebyberg",  # stop_areas: 7181, 17416
    9635: "Djursholms_Ekeby",  # stop_areas: 7171, 60236, 60633, 17414
    9636: "Bråvallavägen",  # stop_areas: 6661, 60233, 17412
    9637: "Djursholms_Ösby",  # stop_areas: 6651, 50371, 17410
    9638: "Mörby_station",  # stop_areas: 7141, 60314
    9200: "Mörby_centrum",  # stop_areas: 2301, 60014, 60017
    9201: "Danderyds_sjukhus",  # stop_areas: 2251, 50366
    9203: "Universitetet",  # stop_areas: 2231, 7111, 51556, 60301, 17398
    9600: "Stockholms_östra",  # stop_areas: 2221, 6601, 10194, 60080, 17399 (Rail terminus)
}

# Bus stops and bus-served locations
BUS_SITE_IDS = {
    7981: "Arninge",  # stop_areas: 7035, 61060 (bus terminal near rail)
    2200: "Roslags_Näsby_trafikplats",  # stop_areas: 60011 (Mycronic/traffic junction)
    2107: "Stocksunds_station",  # stop_areas: 7131, 60601
    1090: "Roslagstull_Ingemarsgatan",  # stop_areas: 10575
    # 1095: "Roslagstull_Roslagsvägen",        # stop_areas: 10101, 10240
    1177: "Universitetet_södra",  # stop_areas: 69011
    5268: "Albano",  # stop_areas: 51091
    9204: "Tekniska_högskolan",  # stop_areas: 2221, 6601, 10194, 60080, 17399 (Metro station with bus)
}

# TODO: add bus lines
LINES = [28]

MODES = [
    "BUS",
    "TRAM",  # Roslagsbanan is designated as a tram
]

# Add delay between requests to avoid hitting API rate limits
DELAY_BETWEEN_REQUESTS_SEC = 1


def fetch_departures(
    site_id: int, lines: list[int] | None = None, modes: list[str] | None = None
):
    """Fetch departures for a given site ID, optionally filtering by lines and modes."""

    response = requests.get(
        BASE_URL.format(siteId=site_id),
        params={"forecast_limit": "30"},  # forecast up to 30 min
    )
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


# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Fetch departures data for each site
for site_id, site_name in SITE_IDS.items():
    data = fetch_departures(site_id=site_id, lines=LINES, modes=MODES)
    with open(os.path.join("data", f"departures_{site_name}.json"), "w") as f:
        json.dump(data, f, indent=2)

    rows = []  # Reset rows for each site
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
                "line_id": line_id,
                "scheduled_time": scheduled_time,
                "expected_time": expected_time,
                "transport_mode": transport_mode,
                "delay": delay,
                "destination": destination,
                "site_id": site_id,
                "journey_id": dep.get("journey").get("id"),
            }
        )

    # Create DataFrame and deduplicate based on journey_id, keeping newest
    csv_file = os.path.join("data", f"departures_{site_name}.csv")
    df_new = pd.DataFrame(rows)

    if os.path.exists(csv_file):
        df_existing = pd.read_csv(csv_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)

        # Remove duplicates based on journey_id, keeping the last (newest) entry from df_new
        df_combined = df_combined.drop_duplicates(subset=["journey_id"], keep="last")
        df_combined.to_csv(csv_file, index=False)
    else:
        df_new.to_csv(csv_file, index=False)

    time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
