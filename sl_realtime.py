import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict
from google.transit import gtfs_realtime_pb2
from datetime import datetime

ROUTES = ["14", "28", "624", "626", "628", "629", "670", "676", "680", "694", "699"]

load_dotenv()
API_KEY = os.getenv("REALTIME_APIKEY", "")
BASE_URL = "https://opendata.samtrafiken.se/gtfs-rt/sl/TripUpdates.pb?key={apikey}"
OUTPUT_FILE = "trip_updates.json"
TRIPS_FILE = "sl/trips.txt"
ROUTES_FILE = "sl/routes.txt"
STOPS_FILE = "sl/stops.txt"
CSV_DIR = "stop_times"


def log(message: str):
    """Log a message with a timestamp."""
    print(f"{datetime.now()}: {message}")


def build_trip_to_route_name(
    trips_file: str, routes_file: str
) -> dict[str, dict[str, str]]:
    """Build a mapping from trip_id to route details"""
    trips = pd.read_csv(
        trips_file, dtype=str, usecols=["route_id", "trip_id", "direction_id"]
    )
    routes = pd.read_csv(
        routes_file, dtype=str, usecols=["route_id", "route_short_name"]
    )
    merged = trips.merge(routes, on="route_id", how="left")
    return {
        row["trip_id"]: {
            "route_short_name": row["route_short_name"],
            "direction_id": row["direction_id"],
        }
        for _, row in merged.iterrows()
    }


def build_stop_id_to_name(stops_file: str) -> dict[str, str]:
    """Build a mapping from stop_id to stop_name"""
    stops = pd.read_csv(stops_file, dtype=str, usecols=["stop_id", "stop_name"])
    return dict(zip(stops["stop_id"], stops["stop_name"]))


def unix_time_to_iso(unix_time: int | str) -> str:
    """Convert a Unix timestamp to ISO format in current timezone"""
    return datetime.fromtimestamp(int(unix_time)).astimezone().isoformat()


def extract_stop_time_rows(data: dict) -> list[dict]:
    """Extract stop time update rows from the GTFS-RT feed data"""
    rows = []
    for entity in data.get("entity", []):
        tu = entity.get("trip_update", {})
        trip = tu.get("trip", {})
        trip_id = trip.get("trip_id")
        start_date = trip.get("start_date")
        timestamp = tu.get("timestamp")
        route_short_name = trip.get("route_short_name")
        direction_id = trip.get("direction_id")
        stop_updates = tu.get("stop_time_update", [])

        # Determine last stop based on the last stop update's stop name (if available)
        last_stop = None
        if stop_updates:
            last_stop = max(stop_updates, key=lambda s: s.get("stop_sequence", 0))
            last_stop = last_stop.get("stop_name")

        for stu in stop_updates:
            arrival = stu.get("arrival", {})
            departure = stu.get("departure", {})
            rows.append(
                {
                    "trip_id": trip_id,
                    "start_date": start_date,
                    "timestamp_unix": timestamp,
                    "timestamp": unix_time_to_iso(timestamp),
                    "route_short_name": route_short_name,
                    "direction_id": direction_id,
                    "last_stop": last_stop,
                    "stop_name": stu.get("stop_name"),
                    "stop_id": stu.get("stop_id"),
                    "arrival_time": arrival.get("time"),
                    "arrival_delay": arrival.get("delay"),
                    "departure_time": departure.get("time"),
                    "departure_delay": departure.get("delay"),
                }
            )
    return rows


def save_stop_time_updates(rows: list[dict]) -> None:
    """
    Save stop time updates to CSV files, one per route.
    Deduplicate rows based on trip_id, stop_id, and start_date, keeping the latest entry based on timestamp
    """
    os.makedirs(CSV_DIR, exist_ok=True)
    new_df = pd.DataFrame(rows)
    for route, group in new_df.groupby("route_short_name"):
        csv_path = os.path.join(CSV_DIR, f"stop_times_{route}.csv")
        if os.path.exists(csv_path):
            existing = pd.read_csv(csv_path, dtype=str)
            combined = pd.concat([existing, group.astype(str)], ignore_index=True)
        else:
            combined = group.astype(str)
        deduped = combined.sort_values("timestamp").drop_duplicates(
            subset=["trip_id", "stop_id", "start_date"], keep="last"
        )
        deduped.to_csv(csv_path, index=False)
        print(f"  {csv_path}: {len(deduped)} rows ({len(group)} new)")


def fetch_trip_updates(api_key: str) -> dict:
    url = BASE_URL.format(apikey=api_key)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return MessageToDict(feed, preserving_proto_field_name=True)


def main():
    trip_to_route = build_trip_to_route_name(TRIPS_FILE, ROUTES_FILE)
    stop_id_to_name = build_stop_id_to_name(STOPS_FILE)

    data = fetch_trip_updates(API_KEY)

    for entity in data.get("entity", []):
        trip_update = entity.get("trip_update", {})
        trip_id = trip_update.get("trip", {}).get("trip_id")
        if trip_id:
            trip_info = trip_to_route.get(trip_id)
            if trip_info:
                trip_update["trip"]["route_short_name"] = trip_info["route_short_name"]
                trip_update["trip"]["direction_id"] = trip_info["direction_id"]
        for stop_update in trip_update.get("stop_time_update", []):
            stop_id = stop_update.get("stop_id")
            if stop_id:
                stop_name = stop_id_to_name.get(stop_id)
                if stop_name:
                    stop_update["stop_name"] = stop_name

    if ROUTES:
        data["entity"] = [
            e
            for e in data.get("entity", [])
            if e.get("trip_update", {}).get("trip", {}).get("route_short_name")
            in ROUTES
        ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log(f"Wrote {len(data.get('entity', []))} entities to {OUTPUT_FILE}")

    rows = extract_stop_time_rows(data)
    save_stop_time_updates(rows)


if __name__ == "__main__":
    main()
