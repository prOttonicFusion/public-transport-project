import requests
import json

# Script to fetch SL traffic deviations data
# https://www.trafiklab.se/api/our-apis/sl/deviations/#openapi-specification

future = True
sites = [
    "7981",  # Arninge
]
sites = []
lines = ["13", "14"]
lines = []
modes = ["BUS", "TRAIN"]


BASE_URL = "https://deviations.integration.sl.se/v1/messages"


def fetch_deviations():
    response = requests.get(
        BASE_URL,
        params={
            "future": str(future).lower(),
            "site": sites,
            "line": lines,
            "transport_mode": modes,
        },
    )
    response.raise_for_status()
    return response.json()


try:
    data = fetch_deviations()
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error fetching deviations: {e}")
