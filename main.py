from datetime import datetime
import logging
from logging import debug
import os
import sys
import csv
import requests


def sync_satcat_csv():
    def pull_and_save_csv():
        res = requests.get("https://celestrak.org/pub/satcat.csv")
        res.raise_for_status()
        with open("satcat.csv", "w") as file:
            file.write(res.text)

    if not os.path.exists("satcat.csv"):
        pull_and_save_csv()
    else:
        # Sync the latest satcat csv from Celestrak if file is older than 1 day
        current_time = datetime.now()
        last_modified = datetime.fromtimestamp(os.path.getmtime("satcat.csv"))
        print(current_time)
        print(last_modified)
        diff = current_time - last_modified
        if diff.days > 0 or int(os.environ.get("FORCE_SYNC_SATCAT")) == 1:
            pull_and_save_csv()


def find_satcat_entry_by_id(satcatId):
    with open("satcat.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["NORAD_CAT_ID"] == str(satcatId):
                return row
        print("No entry found for ID: {satcatId}")
        print("The SATCAT data is valid as of 14/03/2026")
    return None


def get_celestrak_data_by_satcat_id(satcatId: int, format="TLE"):
    """
    Allowed formats are:
    - TLE or 3LE: Three-line element sets including 24-character satellite name on Line 0.
    - 2LE: Two-line element sets (no satellite name on Line 0).
    - XML: CCSDS OMM XML format including all mandatory elements.
    - KVN: CCSDS OMM KVN format including all mandatory elements.
    - JSON: OMM keywords for all GP elements in JSON format.
    - JSON-PRETTY: OMM keywords for all GP elements in JSON pretty-print format.
    - CSV: OMM keywords for all GP elements in CSV format.
    """
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={satcatId}&FORMAT={format.upper()}"
    response = requests.get(url)
    return response.text


def main():
    # Setup
    satcatId = int(sys.argv[1])
    log_level = sys.argv[2] if len(sys.argv) > 2 else "DEBUG"
    logging.basicConfig(level=log_level.upper())
    print(os.environ.get("FORCE_SYNC_SATCAT"))
    print(f"Running issitcoming with satcat ID: {satcatId}")
    sync_satcat_csv()

    # Get satcat entry
    satcat_entry = find_satcat_entry_by_id(satcatId)

    # Show some basic information about the satellite
    if satcat_entry:
        print("Satcat entry found")
        debug(satcat_entry)
        satellite_name = satcat_entry["OBJECT_NAME"]
        satellite_launch_date = satcat_entry["LAUNCH_DATE"]
        satellite_decay_date = satcat_entry["DECAY_DATE"]
        print(f"Name: {satellite_name}")
        print(f"Launch Date: {satellite_launch_date}")
        if satellite_decay_date:
            print(
                f"Satellite will decay/decayed out of orbit on {satellite_decay_date}"
            )

    # Get celestrak data in pretty json format
    celestrak_data = get_celestrak_data_by_satcat_id(satcatId, "2LE")
    print(celestrak_data)


if __name__ == "__main__":
    main()
