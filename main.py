import logging
from logging import debug
import sys
import csv
import requests
from pprint import pprint


def find_satcat_entry_by_id(satcatId):
    with open("satcat.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["NORAD_CAT_ID"] == str(satcatId):
                return row
        print("No entry found for ID: {satcatId}")
        print("The SATCAT data is valid as of 14/03/2026")
    return None


def get_celestrak_data_by_satcat_id(satcatId, format="tle"):
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={satcatId}&FORMAT={format.upper()}"
    response = requests.get(url)
    return response.text


def main():
    # Setup
    satcatId = int(sys.argv[1])
    log_level = sys.argv[2] if len(sys.argv) > 2 else "DEBUG"
    logging.basicConfig(level=log_level.upper())
    print(f"Running issitcoming with satcat ID: {satcatId}")

    # Get satcat entry
    satcat_entry = find_satcat_entry_by_id(satcatId)

    # Show some basic information about the satellite
    if satcat_entry:
        print("Satcat entry found")
        debug(satcat_entry)
        satellite_name = satcat_entry["OBJECT_NAME"]
        satellite_launch_date = satcat_entry["LAUNCH_DATE"]
        print(f"Name: {satellite_name}")
        print(f"Launch Date: {satellite_launch_date}")

    # Get celestrak data
    celestrak_data = get_celestrak_data_by_satcat_id(satcatId)
    print(celestrak_data)


if __name__ == "__main__":
    main()
