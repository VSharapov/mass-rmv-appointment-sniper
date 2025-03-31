#!./venv/bin/python

from playwright.sync_api import sync_playwright
from pprint import pprint as pp
import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import time
import re
import subprocess
import sys

def load_list(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_list(filename, items):
    with open(filename, 'w') as f:
        for item in sorted(items):
            f.write(f"{item}\n")

def is_alert_date(date_str: str) -> bool:
    """Check if a date falls within the alert period."""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date, end_date = load_time_window()
        return start_date <= date < end_date
    except ValueError:
        return False

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

def parse_date_time_group(page, location: str) -> List[Dict[str, Any]]:
    """Parse date/time grouping elements from the page."""
    dates = []
    
    # Find all date columns
    date_columns = page.locator("div.DateTimeGrouping-Column")
    column_count = date_columns.count()
    
    # print(f"\nFound {column_count} date columns")
    
    for col_idx in range(column_count):
        date_column = date_columns.nth(col_idx)
        date_label = date_column.get_attribute("aria-label")
        
        # Parse date from aria-label
        date_match = re.search(r"<p>([A-Za-z]+)</p><p>([A-Za-z]+ \d+, \d{4})</p>", date_label)
        if not date_match:
            print(f"Could not parse date from: {date_label}")
            continue
            
        day_name, full_date = date_match.groups()
        # print(f"\nProcessing date: {full_date} ({day_name})")
        
        # Check if date is within alert window

        location_printed = False
        last_date = None
        outside_time_window = []
        try:
            date_obj = datetime.strptime(full_date, '%b %d, %Y')
            date_str = date_obj.strftime('%Y-%m-%d')
            if is_alert_date(date_str):
                date_data = {
                    'day_name': day_name,
                    'full_date': full_date,
                    'time_groups': []
                }
                
                # Find time groups within this date column
                time_groups = date_column.locator("div.DateTimeGrouping-Group")
                group_count = time_groups.count()
                # print(f"Found {group_count} time groups")
                
                for group_idx in range(group_count):
                    time_group = time_groups.nth(group_idx)
                    group_control = time_group.locator("div.DateTimeGrouping-Control")
                    
                    # Get group info (e.g., "Afternoon")
                    group_title = group_control.locator(".group-title").text_content()
                    available_count = group_control.locator(".group-number").text_content()
                    
                    # print(f"\nTime group: {group_title} ({available_count})")
                    
                    group_data = {
                        'title': group_title,
                        'available_count': available_count,
                        'times': []
                    }
                    
                    # Get available times
                    times = time_group.locator("div.ServiceAppointmentDateTime")
                    time_count = times.count()
                    # print(f"Found {time_count} available times")
                    
                    for time_idx in range(time_count):
                        time_element = times.nth(time_idx)
                        time_text = time_element.text_content()
                        time_data = time_element.get_attribute("data-datetime")
                        
                        # print(f"  Time: {time_text} ({time_data})")
                        
                        group_data['times'].append({
                            'display': time_text,
                            'datetime': time_data
                        })
                        
                        # Alert immediately when a time is found
                        if not location_printed:
                            print(f"{location}: ", end="")
                            location_printed = True
                        if last_date != full_date:
                            print(f"{day_name}, {full_date} - ", end="")
                            last_date = full_date
                        print(f" {time_text}", end="")
                
                date_data['time_groups'].append(group_data)
                dates.append(date_data)
                print()
            else:
                outside_time_window.append(full_date)
            if outside_time_window:
                print(f"There were appointments outside the time window: {outside_time_window[0]} - {outside_time_window[-1]}")
        except ValueError:
            continue
    
    return dates

def get_button_data(button) -> Dict[str, Any]:
    """Extract relevant data from a button element."""
    return {
        'text': button.text_content().strip(),
        'id': button.get_attribute('id'),
        'class': button.get_attribute('class'),
        'type': button.get_attribute('type'),
        'disabled': button.get_attribute('disabled')
    }

def get_page_data(page, location: str, max_retries=3) -> Dict[str, Any]:
    """Collect all relevant data from the current page with retries."""
    data = {
        'buttons': [],
        'timestamp': datetime.now().isoformat(),
        'url': page.url,
        'dates': []
    }
    
    # Wait for the page to be stable
    page.wait_for_load_state("networkidle")
    page.wait_for_load_state("domcontentloaded")
    
    # Add a small delay to ensure the page is fully rendered
    time.sleep(1)
    
    # Try to get button data with retries
    for attempt in range(max_retries):
        try:
            # Get all buttons
            buttons = page.locator("button")
            count = buttons.count()
            
            for i in range(count):
                button = buttons.nth(i)
                data['buttons'].append(get_button_data(button))
            
            # Parse date/time information
            data['dates'] = parse_date_time_group(page, location)
            
            return data
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(1)  # Wait before retry
                continue
            else:
                print(f"Warning: Could not get page data after {max_retries} attempts: {e}")
                return data

def transform_data(all_data: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    """Transform the raw data into a simplified format with dates and times."""
    transformed = {}
    
    for location, location_data in all_data['locations'].items():
        transformed[location] = {}
        
        # Process each page for this location
        for page in location_data['pages']:
            for date_data in page['dates']:
                # Convert date string to ISO format (YYYY-MM-DD)
                try:
                    date_obj = datetime.strptime(date_data['full_date'], '%b %d, %Y')
                    iso_date = date_obj.strftime('%Y-%m-%d')
                except ValueError as e:
                    print(f"Warning: Could not parse date {date_data['full_date']}: {e}")
                    continue
                
                # Initialize the date entry if it doesn't exist
                if iso_date not in transformed[location]:
                    transformed[location][iso_date] = []
                
                # Process each time group
                for time_group in date_data['time_groups']:
                    for time_data in time_group['times']:
                        try:
                            # Convert time string to HH:MM format
                            time_obj = datetime.strptime(time_data['datetime'], '%m/%d/%Y %I:%M:%S %p')
                            time_str = time_obj.strftime('%H:%M')
                            transformed[location][iso_date].append(time_str)
                        except ValueError as e:
                            print(f"Warning: Could not parse time {time_data['datetime']}: {e}")
                            continue
    
    return transformed

def load_url() -> str:
    """Load URL from rmv_url.txt file."""
    try:
        with open('rmv_url.txt', 'r') as f:
            url = f.read().strip()
            print(f"Loaded URL: {url}")
            return url
    except Exception as e:
        print(f"Error loading URL: {e}")
        sys.exit(1)

def test_list_buttons():
    parser = argparse.ArgumentParser(description='Browse RMV locations')
    parser.add_argument('--blacklist', help='Location to add to blacklist')
    args = parser.parse_args()

    # Load persistent lists
    blacklist_file = Path('blacklist.txt')
    whitelist_file = Path('whitelist.txt')
    blacklist = load_list(blacklist_file)
    whitelist = load_list(whitelist_file)
    
    url = load_url()
    
    # Store all collected data
    all_data = {
        'start_time': datetime.now().isoformat(),
        'locations': {}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Set a longer timeout for navigation
        page.set_default_navigation_timeout(30000)
        
        # Go to initial page and wait for it to be ready
        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.wait_for_load_state("domcontentloaded")
        
        # Get all town buttons
        town_buttons = page.locator("button.QflowObjectItem.form-control.ui-selectable")
        town_count = town_buttons.count()
        
        # print(f"Found {town_count} town buttons")
        
        # Process each town
        for i in range(town_count):
            try:
                # Re-get the town buttons after each navigation
                town_buttons = page.locator("button.QflowObjectItem.form-control.ui-selectable")
                town_button = town_buttons.nth(i)
                location = town_button.text_content().strip()
                
                # Skip blacklisted locations
                # print(f"Checking blacklist for {location}:")
                # print(blacklist)
                # print(location in blacklist)
                if location in blacklist:
                    print(f" Blacklist location {i+1}/{town_count}: {location}")
                    continue
                print(f"Processing location {i+1}/{town_count}: {location}")
                
                # Store data for this location
                location_data = {
                    'location': location,
                    'pages': []
                }
                
                # Click the town button and wait for navigation
                # print(f"Clicking town button {i+1}/{town_count}: {location}")
                town_button.click()
                # print("Town button clicked")
                page.wait_for_load_state("networkidle")
                page.wait_for_load_state("domcontentloaded")
                # print("Page loaded")
                
                # Add a small delay to ensure the page is fully rendered
                time.sleep(1)
                
                # Collect data from this page
                location_data['pages'].append(get_page_data(page, location))
                # print("Page data collected")
                
                # Handle both types of Next buttons
                while True:
                    # Check for the form next button
                    form_next = page.locator("button.next-button")
                    # Check for the pagination next button
                    pagination_next = page.locator("div.pagination-label-wrapper[id$='_Next']")
                    
                    if not form_next.is_visible() and not pagination_next.is_visible():
                        break
                    
                    # Try the form next button first
                    if form_next.is_visible() and not form_next.is_disabled():
                        # print("Clicking form next button")
                        form_next.click()
                    # Then try the pagination next button
                    elif pagination_next.is_visible():
                        # print("Clicking pagination next button")
                        pagination_next.click()
                    else:
                        break
                    
                    page.wait_for_load_state("networkidle")
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1)  # Wait for page to stabilize
                    location_data['pages'].append(get_page_data(page, location))
                
                # Store the collected data
                all_data['locations'][location] = location_data
                
                # Go back to the town selection page
                # print("Returning to main page")
                page.goto(url)
                page.wait_for_load_state("networkidle")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1)  # Wait for page to stabilize
                
            except Exception as e:
                print(f"Error processing location {i+1}: {e}")
                # Try to recover by going back to the main page
                try:
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1)
                except:
                    print("Could not recover to main page")
                    break
        
        browser.close()
    
    # Handle blacklist command
    if args.blacklist:
        if args.blacklist not in whitelist:
            print(f"\nError: '{args.blacklist}' is not in the whitelist")
            return
        
        # Remove from whitelist and add to blacklist
        whitelist.remove(args.blacklist)
        blacklist.add(args.blacklist)
        save_list(whitelist_file, whitelist)
        save_list(blacklist_file, blacklist)
        print(f"\nMoved '{args.blacklist}' from whitelist to blacklist")
        return
    
    # Update whitelist with new locations
    current_locations = set(all_data['locations'].keys())
    new_locations = current_locations - blacklist - whitelist
    if new_locations:
        whitelist.update(new_locations)
        save_list(whitelist_file, whitelist)
        print("\nAdded new locations to whitelist:")
        for loc in sorted(new_locations):
            print(f"  {loc}")
    
    # Transform the data into the desired format
    # print("\nTransforming data into simplified format...")
    transformed_data = transform_data(all_data)
    # pp(transformed_data)
    
    # Create data directory if it doesn't exist
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for the filename
    timestamp = int(time.time())
    output_file = data_dir / f"{timestamp}.json"
    
    # Save the transformed data
    with open(output_file, 'w') as f:
        json.dump(transformed_data, f, indent=2)
    
    # print(f"\nTransformed data saved to {output_file}")
    
    # Print a summary of the transformed data
    # print("\nSummary of available appointments:")
    # for location, dates in transformed_data.items():
    #     print(f"\n{location}:")
    #     for date, times in dates.items():
    #         print(f"  {date}: {', '.join(sorted(times))}")
    
    # Launch alert.py in a subprocess
    # print("\nLaunching alert analysis...")
    alert_script = Path(__file__).parent / 'alert.py'
    
    # Print the command that will be executed
    cmd = [str(alert_script), str(output_file)]
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        # Run the subprocess and wait for completion
        result = subprocess.run(
            [sys.executable] + cmd,
            capture_output=True,
            text=True
        )
        
        # Print the output
        if result.stdout:
            print("\nAlert output:")
            print(result.stdout)
        if result.stderr:
            print("\nAlert errors:")
            print(result.stderr)
            
        if result.returncode != 0:
            print(f"\nAlert process exited with code {result.returncode}")
    except Exception as e:
        print(f"Error running alert analysis: {e}")

if __name__ == "__main__":
    test_list_buttons()

