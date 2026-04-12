# Public Transport Project

Comparing Roslagsbanan to buses from a reliability perspective.

## Usage

### Prerequisites

1. Make sure you have Python 3 installed.
2. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

### Data Fetching

#### Departure & Arrival Delays (GTFS)

This script fetches trip updates from the GTFS real-time API and filters for specific routes. Static GTFS data is used to map trip IDs in the update feed to route names and directions.

0. Make sure to have download the static GTFS data into the `sl` directory from: 
   ```
   https://opendata.samtrafiken.se/gtfs/sl/sl.zip?key={apikey}
   ```
1. Run the following command to fetch real-time delay data and save it to `trip_updates.json`:
   ```bash
   python3 sl_realtime.py
   ```

**Note:** The script will append to existing CSV files if they already exist, allowing you to accumulate data over time.

#### Departure delays (REST API)

Run
```bash 
python3 sl_departures.py
```
to fetch real-time departure data for specified sites, lines, and modes. The data will be saved in CSV files named `departures_{site_name}.csv`.

**Note:** The script will append to existing CSV files if they already exist, allowing you to accumulate data over time.