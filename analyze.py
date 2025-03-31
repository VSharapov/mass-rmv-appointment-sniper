#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime
from IPython import embed
from typing import Dict, Any, Tuple
from collections import defaultdict

def load_list(filename: str) -> set:
    """Load a list of items from a file."""
    if not Path(filename).exists():
        return set()
    with open(filename, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def load_data_files() -> Dict[str, Any]:
    """Load all JSON files from the data directory."""
    data_dir = Path('data')
    if not data_dir.exists():
        print("Error: data directory not found")
        return {}
    
    # Get all JSON files in the data directory
    json_files = list(data_dir.glob('*.json'))
    if not json_files:
        print("No JSON files found in data directory")
        return {}
    
    # Load all data files
    all_data = {
        'timestamps': [],
        'data': {}
    }
    
    for json_file in json_files:
        timestamp = json_file.stem  # Get filename without extension
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                all_data['timestamps'].append(timestamp)
                all_data['data'][timestamp] = data
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    # Sort timestamps chronologically
    all_data['timestamps'].sort()
    
    return all_data

def filter_blacklisted_locations(data: Dict[str, Any], blacklist: set) -> Dict[str, Any]:
    """Filter out blacklisted locations from the data."""
    filtered_data = {
        'timestamps': data['timestamps'],
        'data': {}
    }
    
    for timestamp, timestamp_data in data['data'].items():
        filtered_data['data'][timestamp] = {
            location: location_data 
            for location, location_data in timestamp_data.items() 
            if location not in blacklist
        }
    
    return filtered_data

def analyze_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the data and extract key information."""
    analysis = {
        'locations': set(),
        'dates': set(),
        'earliest_appointment': None
    }
    
    # Track all locations and dates
    for timestamp, timestamp_data in data['data'].items():
        for location, location_data in timestamp_data.items():
            analysis['locations'].add(location)
            for date in location_data.keys():
                analysis['dates'].add(date)
    
    # Sort locations and dates
    analysis['locations'] = sorted(analysis['locations'])
    analysis['dates'] = sorted(analysis['dates'])
    
    # Find earliest appointment
    earliest_time = None
    earliest_info = None
    
    for timestamp, timestamp_data in data['data'].items():
        for location, location_data in timestamp_data.items():
            for date, times in location_data.items():
                if not times:
                    continue
                    
                # Convert date and first time to datetime
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    time_obj = datetime.strptime(times[0], '%H:%M')
                    appointment_dt = datetime.combine(date_obj.date(), time_obj.time())
                    
                    if earliest_time is None or appointment_dt < earliest_time:
                        earliest_time = appointment_dt
                        earliest_info = {
                            'datetime': appointment_dt,
                            'date': date,
                            'time': times[0],
                            'location': location,
                            'timestamp': timestamp
                        }
                except ValueError as e:
                    print(f"Warning: Could not parse date/time: {date} {times[0]}: {e}")
    
    analysis['earliest_appointment'] = earliest_info
    
    return analysis

def main():
    # Load blacklist
    blacklist = load_list('blacklist.txt')
    if blacklist:
        print(f"Loaded {len(blacklist)} blacklisted locations")
    
    # Load all data
    print("Loading data files...")
    data = load_data_files()
    
    if not data['timestamps']:
        print("No data loaded. Exiting.")
        return
    
    print(f"\nLoaded {len(data['timestamps'])} data files")
    print(f"Timestamps: {', '.join(data['timestamps'])}")
    
    # Filter out blacklisted locations
    if blacklist:
        print("\nFiltering out blacklisted locations...")
        data = filter_blacklisted_locations(data, blacklist)
    
    # Analyze the data
    print("\nAnalyzing data...")
    analysis = analyze_data(data)
    
    # Print analysis results
    print("\n=== Analysis Results ===")
    print(f"\nTotal Locations: {len(analysis['locations'])}")
    print("Locations:")
    for location in analysis['locations']:
        print(f"  - {location}")
    
    print(f"\nTotal Unique Dates: {len(analysis['dates'])}")
    print("Dates:")
    for date in analysis['dates']:
        print(f"  - {date}")
    
    if analysis['earliest_appointment']:
        earliest = analysis['earliest_appointment']
        print(f"\nEarliest Available Appointment:")
        print(f"  Location: {earliest['location']}")
        print(f"  Date: {earliest['date']}")
        print(f"  Time: {earliest['time']}")
        print(f"  Seen at timestamp: {earliest['timestamp']}")
        print(f"  Full datetime: {earliest['datetime']}")
    
    # Create some useful variables for the interactive shell
    timestamps = data['timestamps']
    raw_data = data['data']
    
    # Drop into IPython shell
    print("\nDropping into IPython shell...")
    print("Available variables:")
    print("  - timestamps: List of all timestamps")
    print("  - raw_data: Dictionary mapping timestamps to their data")
    print("  - data: Complete data structure")
    print("  - analysis: Analysis results")
    print("  - blacklist: Set of blacklisted locations")
    embed()

if __name__ == "__main__":
    main() 