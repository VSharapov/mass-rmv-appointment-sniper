# Mass RMV Appointent Sniper

## Overview

Originally called the **RMV Appointment Dingler**

- The RMV REAL ID scheduling site provides a list of locations with appointment availability.
- Clicking a location often leads to “No appointments” because slots are taken quickly.
- Most appointments are in remote or inconvenient areas (e.g., Western MA, Martha’s Vineyard).
- Appointments become available at seemingly random intervals due to user cancellations.

- Automatically scan appointment availability across all RMV locations.
- Filter results by:
  - Location (by slowly growing a blacklist).
  - Time window.
- Immediate alert on a match.
  - Helper link with a gMaps search to see if it's close.
  - Helper popups - your scheduling page and the name of the matching location.

## Quickstart

1. Clone the repository:
   ```bash
   git clone https://github.com/VSharapov/mass-rmv-appointment-sniper.git
   cd mass-rmv-appointment-sniper
   ```

2. Set up the Python environment and install dependencies:
   ```bash
   ./setup.sh
   ```

3. Put your appointment scheduling URL into `rmv_url.txt`

4. Edit `time_window.json` to your liking

5. Run the appointment sniper:
   ```bash
   # Run once
   ./browse.py

   # Or run continuously (checking every minute)
   until read -n1 -t60; do timeout 999 ./browse.py; echo "Next: $(date -d+1min -R)"; done
   ```

6. When an appointment is found:
   - The script will automatically open the RMV booking page
   - A helper page will show the matching location
   - Use the provided Google Maps link to check convenience
   - Use suggested blacklist command to expand it
   - Use suggested command to close the time window to exclude the matching date

## Project Structure (Current)

### 1. `browse.py`
- Uses **Playwright** to navigate RMV booking.
- Generates a structured object, e.g.:

    ```json
    {
    "Danvers8 Newbury Street, Danvers MA, 01923": {
        "2025-04-10": [
        "13:20",
        "13:30",
        "13:40"
        ]
    },
    "Lawrence73C Winthrop Avenue, Lawrence MA, 01843": {},
    "Lowell77 Middlesex Street, Lowell MA, 01852": {},
    "Wilmington355 Middlesex Avenue, Wilmington MA, 01887": {}
    }
    ```

- Saves this JSON to the `data/` directory using Unix epoch timestamps as filenames.
- Triggers `alert.py`, passing the name of the JSON file as a parameter.

### 2. `alert.py`
- Parses the JSON availability file.
- Filters out blacklisted locations and out-of-window times.
- Formats results into a clean, terminal-friendly output:
  - Office name
  - Google Maps search link
  - Suggest command to add location `>> blacklist.txt`
  - Suggest command for shrinking the time window
- Automatically opens:
  - RMV appointment booking link.
  - A helper web page showing the chosen location to make it easier to spot on the official site.

### 3. `setup.sh`
- Creates a Python virtual environment.
- Installs Playwright and required dependencies.
- Executes `playwright install` to fetch necessary browser binaries.

## Future Improvements

- Merge `browse.py` and `alert.py`
- Currently I invoke: `until read -n1 -t60; do timeout 999 ./browse.py; echo "Next: $(date -d+1min -R)"; done`
  - Handle playwright taking forever
  - Handle sleeping between scrapes
- Configurable browser (not just Firefox).
- Analytics on `data/*.json` (e.g., Grafana)
