# quant_astro/dasha_logic.py

import csv
import re
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import pytz
import pkg_resources

# --- Configuration & Constants (from notebook) ---
getcontext().prec = 20 # Set high precision for Decimal calculations

PLANET_CYCLE = {
    'Ke': {'value': 7, 'next': 'Ve'}, 'Ve': {'value': 20, 'next': 'Su'},
    'Su': {'value': 6, 'next': 'Mo'}, 'Mo': {'value': 10, 'next': 'Ma'},
    'Ma': {'value': 7, 'next': 'Ra'}, 'Ra': {'value': 18, 'next': 'Ju'},
    'Ju': {'value': 16, 'next': 'Sa'}, 'Sa': {'value': 19, 'next': 'Me'},
    'Me': {'value': 17, 'next': 'Ke'}
}

# --- Helper Functions (from notebook) ---
def _parse_timezone(tz_str):
    match = re.match(r'^([+-]?)(\\d{1,2})(:?)(\\d{0,2})$', tz_str)
    sign = -1 if match.group(1) == '-' else 1
    hours = float(match.group(2))
    mins = float(match.group(4) or 0)
    return sign * (hours + mins/60)

def _add_seconds(dt, seconds):
    total_seconds = Decimal(str(seconds))
    days, remainder_seconds = divmod(total_seconds, Decimal('86400'))
    seconds_int = int(remainder_seconds)
    microseconds = int((remainder_seconds - seconds_int) * 1_000_000)
    delta = timedelta(days=int(days), seconds=seconds_int, microseconds=microseconds)
    return dt + delta

def _subtract_seconds(dt, seconds):
    return _add_seconds(dt, -Decimal(str(seconds)))

def _divide_interval(main_planet, start, end, level, max_level):
    """Recursive function to divide time intervals into sub-periods."""
    current_and_deeper_intervals = []
    sub_periods_at_this_level = []
    current_planet_name = main_planet
    current_start = start
    parent_total_seconds = Decimal((end - start).total_seconds())

    for _ in range(9):
        planet_years = Decimal(PLANET_CYCLE[current_planet_name]['value'])
        sub_seconds = (parent_total_seconds * planet_years) / Decimal(120)
        current_end = current_start + timedelta(seconds=float(sub_seconds))
        sub_periods_at_this_level.append((f"L{level} {current_planet_name}", current_start, current_end))
        current_planet_name = PLANET_CYCLE[current_planet_name]['next']
        current_start = current_end

    current_and_deeper_intervals.extend(sub_periods_at_this_level)

    if level < max_level:
        for name, sub_start, sub_end in sub_periods_at_this_level:
            sub_main_planet = name.split()[-1]
            deeper_intervals = _divide_interval(sub_main_planet, sub_start, sub_end, level + 1, max_level)
            current_and_deeper_intervals.extend(deeper_intervals)

    return current_and_deeper_intervals

def _generate_dasha_periods(planet_positions, birth_config, dasa_config):
    """Main internal function to orchestrate Dasha period calculation."""
    # --- 1. Unpack configs ---
    LOCAL_TIME_STR = birth_config["local_time_str"]
    TIMEZONE = birth_config["timezone_str"]
    MAX_LEVEL = dasa_config["max_level"]
    OUTPUT_MODE = dasa_config["output_mode"]
    DAYS_IN_YEAR = dasa_config["days_in_year"]

    # --- 2. Calculate Dasha Balance (E) ---
    moon_lon = Decimal(str(planet_positions['Mo']['lon']))
    
    # IMPORTANT: Use pkg_resources to find the data file within the package
    star_file_path = pkg_resources.resource_filename('quant_astro', 'data/star.csv')
    with open(star_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        star_data = list(reader)

    moon_star = None
    for entry in star_data:
        from_deg = Decimal(entry['From'])
        to_deg = Decimal(entry['To']) if Decimal(entry['To']) != Decimal('0') else Decimal('360')
        if from_deg <= moon_lon < to_deg:
            moon_star = entry
            break
    if not moon_star:
        raise ValueError("Could not find the Moon's star ruler (Nakshatra).")

    F = moon_lon - Decimal(moon_star['From'])
    A = Decimal(str(DAYS_IN_YEAR)) * Decimal('86400')
    B = Decimal(moon_star['YearNumber'])
    C = B * A
    D = C * F
    E_seconds = D / Decimal('13.333333333333334') # Dasha balance in seconds

    # --- 3. Calculate Dasha Start Time ---
    initial_time = datetime.strptime(LOCAL_TIME_STR, "%Y-%m-%d %H:%M:%S.%f")
    timezone_offset = _parse_timezone(TIMEZONE)
    local_tz = pytz.FixedOffset(int(timezone_offset*60))
    initial_utc = local_tz.localize(initial_time).astimezone(pytz.utc)
    dasha_start_utc = _subtract_seconds(initial_utc, E_seconds)
    current_time = dasha_start_utc.astimezone(local_tz)

    # --- 4. Generate All Dasha Levels ---
    planet_seconds = {p: Decimal(d['value']) * A for p, d in PLANET_CYCLE.items()}

    # Generate Level 1 intervals
    level1_intervals = []
    start_time = current_time
    current_planet = moon_star['Star-Lord']
    for _ in range(9):
        end_time = _add_seconds(start_time, planet_seconds[current_planet])
        level1_intervals.append((f"L1 {current_planet}", start_time, end_time))
        start_time = end_time
        current_planet = PLANET_CYCLE[current_planet]['next']

    # Generate deeper levels
    deeper_intervals_all = []
    for l1_name, l1_start, l1_end in level1_intervals:
        main_planet = l1_name.split()[-1]
        deeper_intervals_all.extend(_divide_interval(main_planet, l1_start, l1_end, 2, MAX_LEVEL))

    # Combine based on output mode
    all_intervals = []
    if OUTPUT_MODE == "all":
        all_intervals.extend(level1_intervals)
    all_intervals.extend(deeper_intervals_all)
    all_intervals.sort(key=lambda x: x[1])

    return all_intervals