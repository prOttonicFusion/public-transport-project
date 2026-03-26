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

#### Departure delays: 

Run
```bash 
python3 sl_departures.py
```
to fetch real-time departure data for specified sites, lines, and modes. The data will be saved in CSV files named `departures_{site_name}.csv`.

**Note:** The script will append to existing CSV files if they already exist, allowing you to accumulate data over time.