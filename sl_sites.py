import requests
import json

# Script to fetch SL traffic deviations data

# Hardcoded parameters
future = True
sites = ["1002", "1003"]
lines = ["13", "14"]
modes = ["BUS", "TRAIN", "TRAM"]


BASE_URL = "https://deviations.integration.sl.se/v1/messages"


def list_sites():
    response = requests.get("https://transport.integration.sl.se/v1/sites?expand=true")
    response.raise_for_status()
    return response.json()


try:
    data = list_sites()
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error fetching: {e}")
