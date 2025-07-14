# quant_astro/api.py

import pandas as pd
from IPython.display import display, FileLink
import os

from .core import calculate_positions
from .dasha_Vimshottari  import _generate_dasha_periods # Internal logic

def create_dasha_table(birth_config, dasa_config, output_filename="dasha_table.csv"):
    """
    Generates a Vimshottari Dasha table based on birth details and downloads it as a CSV.

    This function is designed to be called from a Jupyter Notebook or similar environment
    to enable the automatic download functionality.

    Args:
        birth_config (dict): A dictionary containing birth information.
            - "local_time_str": "YYYY-MM-DD HH:MM:SS.ffffff"
            - "timezone_str": "+HH:MM" or "+H.H"
            - "latitude_str": "DD°MM'SS.ffffff\""
            - "longitude_str": "DD°MM'SS.ffffff\""
            - "elevation": float
        dasa_config (dict): A dictionary containing Dasha calculation settings.
            - "max_level": int (e.g., 4)
            - "output_mode": "all" or "present"
            - "days_in_year": float (e.g., 365.25)
        output_filename (str): The name for the output CSV file.
    """
    print("Step 1: Calculating planetary positions...")
    # Call the core function to get planetary positions
    planet_positions, _, _, _ = calculate_positions(
        local_time_str=birth_config["local_time_str"],
        timezone_str=birth_config["timezone_str"],
        latitude_str=birth_config["latitude_str"],
        longitude_str=birth_config["longitude_str"],
        elevation=birth_config["elevation"]
    )
    print("Step 2: Generating Dasha periods. This may take a moment...")
    # Pass the results and configs to the internal logic to get all time intervals
    all_intervals = _generate_dasha_periods(planet_positions, birth_config, dasa_config)

    print(f"Step 3: Formatting data for {len(all_intervals)} periods...")
    # Convert the results into a structured list for DataFrame creation
    output_data = []
    for name, start, _ in all_intervals:
        level_planet = name.split()
        level = level_planet[0][1:]
        planet = level_planet[1]
        start_str = start.strftime('%Y-%m-%d %H:%M:%S.%f')
        output_data.append([level, planet, start_str])

    # Create a pandas DataFrame
    df = pd.DataFrame(output_data, columns=["Level", "Planet", "Date"])

    print(f"Step 4: Saving to '{output_filename}' and creating download link...")
    # Save the DataFrame to a CSV file
    df.to_csv(output_filename, index=False, encoding='utf-8')

    # Display a download link in the notebook
    display(FileLink(output_filename))
    print(f"\n✅ Success! The Dasha table has been generated.")
    print(f"If the download doesn't start automatically, click the link above: '{output_filename}'")