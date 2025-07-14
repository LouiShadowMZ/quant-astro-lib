# quant_astro/api.py

import pytz
import csv
import pandas as pd
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
from IPython.display import display, FileLink

# We import the core calculation function from your existing 'core.py'
from .core import calculate_positions, _parse_timezone

# --- Main User-Facing Function ---
def create_dasha_table(birth_config, dasa_config, star_chart_path):
    """
    Calculates the Dasha table based on birth data and triggers a download.

    Args:
        birth_config (dict): A dictionary containing birth details.
        dasa_config (dict): A dictionary containing Dasha calculation settings.
        star_chart_path (str): The file path to the 'star.csv' file.
    """
    # Set precision for decimal calculations
    getcontext().prec = 50

    # --- Part 1: Initial Planet Position Calculation ---
    # This part calls your existing 'calculate_positions' function
    planet_positions, _, _, _ = calculate_positions(
        local_time_str=birth_config["local_time_str"],
        timezone_str=birth_config["timezone_str"],
        latitude_str=birth_config["latitude_str"],
        longitude_str=birth_config["longitude_str"],
        elevation=birth_config["elevation"]
    )
    moon_lon = Decimal(str(planet_positions['Mo']['lon']))

    # --- Part 2: Calculate Time Deduction (E_seconds) ---
    # This logic is adapted from your notebook
    moon_star, from_deg = _find_moon_star(moon_lon, star_chart_path)
    if not moon_star:
        raise ValueError("Could not find the Moon's star nakshatra.")

    F = moon_lon - from_deg
    days_in_year = Decimal(str(dasa_config["days_in_year"]))
    A = days_in_year * Decimal('86400')
    B = Decimal(moon_star['YearNumber'])
    C = B * A
    D = C * F
    E_seconds = D / Decimal('13.333333333333333333333333333333')

    # --- Part 3: Calculate Dasha Start Time ---
    # This logic is also from your notebook
    initial_time = datetime.strptime(birth_config["local_time_str"], "%Y-%m-%d %H:%M:%S.%f")
    timezone_offset = _parse_timezone(birth_config["timezone_str"])
    local_tz = pytz.FixedOffset(int(timezone_offset * 60))
    initial_utc = local_tz.localize(initial_time).astimezone(pytz.utc)
    dasha_start_utc = initial_utc - timedelta(seconds=float(E_seconds))

    # --- Part 4: Generate All Dasha Periods ---
    # This combines the final logic from your notebook
    all_intervals = _generate_all_intervals(
        dasha_start_utc.astimezone(local_tz),
        moon_star['Star-Lord'],
        dasa_config,
        A
    )

    # --- Part 5: Create DataFrame and Trigger Download ---
    # MODIFICATION: Instead of writing a CSV and then downloading, we create a
    # pandas DataFrame and use IPython to make it downloadable.
    df = pd.DataFrame(all_intervals, columns=['Level', 'Planet', 'Start Date'])
    
    # Format the 'Start Date' column for better readability
    df['Start Date'] = pd.to_datetime(df['Start Date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    output_filename = "dasha_table.csv"
    df.to_csv(output_filename, index=False)

    print(f"Dasha table generated successfully. Click the link below to download:")
    display(FileLink(output_filename)) # This creates the download link

    return df # Also return the DataFrame for programmatic use


# --- Helper Functions (Adapted from your dasha.ipynb) ---

def _find_moon_star(moon_lon, star_chart_path):
    """Finds the nakshatra the Moon is in."""
    with open(star_chart_path, mode='r') as file:
        reader = csv.DictReader(file)
        for entry in reader:
            from_deg = Decimal(entry['From'])
            to_deg = Decimal(entry['To'])
            # Handle the 0-degree crossover for Revati
            if from_deg > to_deg: 
                if moon_lon >= from_deg or moon_lon < to_deg:
                    return entry, from_deg
            elif from_deg <= moon_lon < to_deg:
                return entry, from_deg
    return None, None

def _generate_all_intervals(start_time, start_planet_lord, dasa_config, year_in_seconds):
    """Generates the full list of Dasha intervals."""
    planet_cycle = {
        'Ke': {'value': 7, 'next': 'Ve'}, 'Ve': {'value': 20, 'next': 'Su'},
        'Su': {'value': 6, 'next': 'Mo'}, 'Mo': {'value': 10, 'next': 'Ma'},
        'Ma': {'value': 7, 'next': 'Ra'}, 'Ra': {'value': 18, 'next': 'Ju'},
        'Ju': {'value': 16, 'next': 'Sa'}, 'Sa': {'value': 19, 'next': 'Me'},
        'Me': {'value': 17, 'next': 'Ke'}
    }
    planet_seconds = {p: Decimal(d['value']) * year_in_seconds for p, d in planet_cycle.items()}

    # Generate Level 1 intervals
    level1_intervals = []
    current_time = start_time
    current_planet = start_planet_lord
    for _ in range(9):
        end_time = current_time + timedelta(seconds=float(planet_seconds[current_planet]))
        level1_intervals.append((f"L1 {current_planet}", current_time, end_time))
        current_time = end_time
        current_planet = planet_cycle[current_planet]['next']

    # Generate deeper intervals
    deeper_intervals_all = []
    for name, l1_start, l1_end in level1_intervals:
        main_planet = name.split()[-1]
        deeper_intervals_all.extend(
            _divide_interval_recursive(main_planet, l1_start, l1_end, 2, dasa_config["max_level"], planet_cycle)
        )

    # Combine based on output_mode
    if dasa_config["output_mode"] == "all":
        final_intervals = level1_intervals + deeper_intervals_all
    else: # "present" mode
        final_intervals = [
            interval for interval in deeper_intervals_all
            if int(interval[0].split()[0][1:]) == dasa_config["max_level"]
        ]

    final_intervals.sort(key=lambda x: x[1])

    # Format for DataFrame
    formatted_list = []
    for name, start, _ in final_intervals:
        level, planet = name.split()
        formatted_list.append([int(level[1:]), planet, start])

    return formatted_list


def _divide_interval_recursive(main_planet, start, end, level, max_level, planet_cycle):
    """Recursively divides a Dasha period."""
    if level > max_level:
        return []

    intervals = []
    parent_duration = (end - start).total_seconds()
    current_start = start
    current_planet = main_planet
    
    # Generate this level's intervals
    for _ in range(9):
        planet_years = Decimal(planet_cycle[current_planet]['value'])
        sub_duration_seconds = (Decimal(parent_duration) * planet_years) / Decimal(120)
        current_end = current_start + timedelta(seconds=float(sub_duration_seconds))
        intervals.append((f"L{level} {current_planet}", current_start, current_end))
        current_planet = planet_cycle[current_planet]['next']
        current_start = current_end

    # Recurse for deeper levels
    all_sub_intervals = list(intervals)
    for name, sub_start, sub_end in intervals:
        sub_main_planet = name.split()[-1]
        all_sub_intervals.extend(
            _divide_interval_recursive(sub_main_planet, sub_start, sub_end, level + 1, max_level, planet_cycle)
        )
        
    return all_sub_intervals