import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict
from google.transit import gtfs_realtime_pb2

ROUTES = ["14", "28", "624", "626", "628", "629", "670", "676", "680", "694", "699"]

# Load environment variables
load_dotenv()
API_KEY = os.getenv("REALTIME_APIKEY", "")
BASE_URL = "https://opendata.samtrafiken.se/gtfs-rt/sl/TripUpdates.pb?key={apikey}"
OUTPUT_FILE = "trip_updates.json"
TRIPS_FILE = "sl/trips.txt"
ROUTES_FILE = "sl/routes.txt"
STOPS_FILE = "sl/stops.txt"


def build_trip_to_route_name(trips_file: str, routes_file: str) -> dict[str, str]:
    trips = pd.read_csv(trips_file, dtype=str, usecols=["route_id", "trip_id"])
    routes = pd.read_csv(
        routes_file, dtype=str, usecols=["route_id", "route_short_name"]
    )
    merged = trips.merge(routes, on="route_id", how="left")
    return dict(zip(merged["trip_id"], merged["route_short_name"]))


def build_stop_id_to_name(stops_file: str) -> dict[str, str]:
    stops = pd.read_csv(stops_file, dtype=str, usecols=["stop_id", "stop_name"])
    return dict(zip(stops["stop_id"], stops["stop_name"]))


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
            route_name = trip_to_route.get(trip_id)
            if route_name:
                trip_update["trip"]["route_short_name"] = route_name
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

    print(f"Wrote {len(data.get('entity', []))} entities to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
