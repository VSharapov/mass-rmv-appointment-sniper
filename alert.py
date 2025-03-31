#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import subprocess

def load_list(filename: str) -> set:
    """Load a list of items from a file."""
    if not Path(filename).exists():
        return set()
    with open(filename, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def load_time_window() -> tuple[datetime, datetime]:
    """Load start and end dates from time_window.json."""
    try:
        with open('time_window.json', 'r') as f:
            window = json.load(f)
            start_date = datetime.strptime(window['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(window['end_date'], '%Y-%m-%d')
            return start_date, end_date
    except Exception as e:
        print(f"Error loading time window: {e}")
        # Fallback to default dates
        return datetime(2025, 3, 24), datetime(2025, 4, 24)

def is_alert_date(date_str: str) -> bool:
    """Check if a date falls within the alert period."""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date, end_date = load_time_window()
        return start_date <= date < end_date
    except ValueError:
        return False

def load_url() -> str:
    """Load URL from rmv_url.txt file."""
    try:
        with open('rmv_url.txt', 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error loading URL: {e}")
        sys.exit(1)

def analyze_appointments(data_file: str):
    """Analyze appointments and alert on specific conditions."""
    url = load_url()
    # Load blacklist
    blacklist = load_list('blacklist.txt')
    # if blacklist:
    #     print(f"Loaded {len(blacklist)} blacklisted locations")
    
    # Load appointment data
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading data file: {e}")
        return
    
    # Track alerts
    alerts = []
    match_found = False
    
    # Analyze each location
    for location, dates in data.items():
        # Skip blacklisted locations
        if location in blacklist:
            continue
            
        # Check each date
        # print(dates.items())
        for date, times in dates.items():
            if is_alert_date(date):
                alerts.append({
                    'location': location,
                    'date': date,
                    'times': sorted(times),
                    'url': url
                })
                
                if times:
                    match_found = True
    
    # Print alerts
    if alerts:
        print("\n=== ALERT: Available Appointments Found ===")
        locations_printed = []
        for alert in alerts:
            if alert['location'] not in locations_printed:
                locations_printed.append(alert['location'])
                print(f"\n{alert['location']} on {datetime.strptime(alert['date'], '%Y-%m-%d').strftime('%A')}, {alert['date']} at {', '.join(alert['times'])}")
                print(f"https://www.google.com/maps/search/{alert['location'].replace(' ', '+')}/@42.18,-72.51,9z/")
                print(f"To blacklist this location:")
                escaped = alert['location'].replace("'", "'\\''")
                print(f"  echo '{escaped}' >> blacklist.txt")
                print(f"To make the time window close before {alert['date']}:")
                print(f"  jq --arg date '{alert['date']}' '.end_date = $date' time_window.json > tmp.json && mv tmp.json time_window.json")
    # else:
    #     print("\nNo alerts triggered for this data.")
    
    if match_found:
        print("\nMatching appointments found! Launching Firefox...")
        try:
            subprocess.run(['firefox', url], check=True, stderr=subprocess.DEVNULL)
            # print("Firefox launched successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error launching Firefox: {e}")
        except FileNotFoundError:
            print("Firefox not found in PATH")
        unique_locations=[]
        for alert in alerts:
            if alert['location'] not in unique_locations:
                unique_locations.append(alert['location'])
                try:
                    subprocess.run(['firefox', f"https://vas.im/firefox-alert/?alertText={alert['location']}"], check=True, stderr=subprocess.DEVNULL)
                    # print("Firefox launched successfully")
                except subprocess.CalledProcessError as e:
                    print(f"Error launching Firefox: {e}")
                except FileNotFoundError:
                    print("Firefox not found in PATH")

def main():
    if len(sys.argv) != 2:
        print("Usage: alert.py <data_file>")
        sys.exit(1)
    
    data_file = sys.argv[1]
    analyze_appointments(data_file)

if __name__ == "__main__":
    main() 