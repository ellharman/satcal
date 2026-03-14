import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
from io import StringIO
from logging import debug

import requests
from skyfield.api import EarthSatellite, load, wgs84


def _cache_dir() -> str:
    """
    Return the base cache directory for satcal, creating it if necessary.
    """
    # Follow XDG-style cache convention, e.g. ~/.cache/satcal
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "satcal")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def sync_satcat_csv() -> None:
    satcat_path = os.path.join(_cache_dir(), "satcat.csv")

    def pull_and_save_csv() -> None:
        res = requests.get("https://celestrak.org/pub/satcat.csv")
        res.raise_for_status()
        with open(satcat_path, "w") as file:
            file.write(res.text)

    if not os.path.exists(satcat_path):
        pull_and_save_csv()
    else:
        # Sync the latest satcat csv from Celestrak if file is older than 1 day
        current_time = datetime.now()
        last_modified = datetime.fromtimestamp(os.path.getmtime(satcat_path))
        diff = current_time - last_modified
        if diff.days > 0 or int(os.environ.get("FORCE_SYNC_SATCAT", 0)) == 1:
            pull_and_save_csv()


def find_satcat_entry_by_id(satcat_id: int) -> dict | None:
    satcat_path = os.path.join(_cache_dir(), "satcat.csv")
    with open(satcat_path, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["NORAD_CAT_ID"] == str(satcat_id):
                return row
        debug(f"No entry found for ID: {satcat_id}")
        debug("The SATCAT data is valid as of 14/03/2026")
    return None


def get_celestrak_data_by_satcat_id(satcat_id: int, format: str = "TLE") -> str:
    """
    Allowed formats are:
    - TLE or 3LE: Three-line element sets including 24-character satellite name on Line 0.
    - 2LE: Two-line element sets (no satellite name on Line 0).
    - XML: CCSDS OMM XML format including all mandatory elements.
    - KVN: CCSDS OMM KVN format including all mandatory elements.
    - JSON: OMM keywords for all GP elements in JSON format.
    - JSON-PRETTY: OMM keywords for all GP elements in JSON pretty-debug format.
    - CSV: OMM keywords for all GP elements in CSV format.
    """
    # Cache under the user's home directory (e.g. ~/.satcal/cache)
    cache_dir = os.path.join(os.path.expanduser("~"), ".satcal", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = f"{satcat_id}_{format.upper()}"
    cache_path = os.path.join(cache_dir, f"celestrak_{cache_key}.json")

    now = datetime.now().timestamp()
    max_age_seconds = 6 * 60 * 60  # 6 hours

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
            fetched_at = float(cached.get("fetched_at", 0))
            if now - fetched_at <= max_age_seconds:
                return str(cached.get("data", ""))
        except Exception:
            # Ignore cache errors and fall back to network
            pass

    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={satcat_id}&FORMAT={format.upper()}"
    response = requests.get(url)
    response.raise_for_status()
    text = response.text

    try:
        with open(cache_path, "w") as f:
            json.dump({"fetched_at": now, "data": text}, f)
    except Exception:
        # If we can't write the cache, still return the live data
        pass

    return text


def create_sat_entity_from_omm_csv(ts, csv_string: str) -> EarthSatellite:
    f = StringIO(csv_string)
    data = csv.DictReader(f)
    sat = [EarthSatellite.from_omm(ts, fields) for fields in data][0]
    return sat


def find_visible_passes(
    sat: EarthSatellite, location, eph, ts, hours_ahead: int = 6
) -> list[dict]:
    t0 = ts.now()
    t1 = ts.now() + (hours_ahead / 24)

    # Find rise/culmination/set events above 20°
    t, events = sat.find_events(location, t0, t1, altitude_degrees=20)
    # events: 0 = rise, 1 = culmination (max elevation), 2 = set

    event_labels = ["rise", "peak", "set"]
    passes: list[dict] = []
    current_pass: dict = {}

    for ti, event in zip(t, events):
        name = event_labels[event]
        difference = sat - location
        topocentric = difference.at(ti)
        alt, az, _ = topocentric.altaz()

        sat_sunlit = sat.at(ti).is_sunlit(eph)
        observer_dark = not location.at(ti).is_sunlit(eph)
        visible = sat_sunlit and observer_dark

        current_pass[name] = {
            "time": ti.utc_iso(),
            "alt": float(alt.degrees),
            "az": float(az.degrees),
            "visible": bool(visible),
        }

        if name == "set":
            passes.append(current_pass)
            current_pass = {}

    return passes


def run(
    satcat_id: int,
    user_lat: float,
    user_lon: float,
    hours_ahead: int,
    verbose: bool = False,
) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    debug(f"Running with satcat ID: {satcat_id}")

    sync_satcat_csv()
    ephemeris = load("de421.bsp")
    ts = load.timescale()

    # Get satcat entry
    satcat_entry = find_satcat_entry_by_id(satcat_id)

    # Show some basic information about the satellite
    if satcat_entry:
        debug("Satcat entry found")
        debug(satcat_entry)
        satellite_name = satcat_entry["OBJECT_NAME"]
        satellite_launch_date = satcat_entry["LAUNCH_DATE"]
        satellite_decay_date = satcat_entry["DECAY_DATE"]
        debug(f"Name: {satellite_name}")
        debug(f"Launch Date: {satellite_launch_date}")
        if satellite_decay_date:
            debug(
                f"Satellite will decay/decayed out of orbit on {satellite_decay_date}"
            )

    # Init the satellite
    omm_csv = get_celestrak_data_by_satcat_id(satcat_id, "CSV")
    sat = create_sat_entity_from_omm_csv(ts, omm_csv)

    passes = find_visible_passes(
        sat, wgs84.latlon(user_lat, user_lon), ephemeris, ts, hours_ahead
    )

    json.dump(passes, fp=sys.stdout)
    print()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="satcal",
        description=(
            "Predict when an Earth–orbiting satellite will be visible from your "
            "location in the next few hours."
        ),
    )
    parser.add_argument("satcat_id", type=int, help="NORAD catalog ID of the satellite")
    parser.add_argument(
        "latitude", type=float, help="Observer latitude in decimal degrees"
    )
    parser.add_argument(
        "longitude", type=float, help="Observer longitude in decimal degrees"
    )
    parser.add_argument(
        "hours_ahead",
        type=int,
        help="How many hours ahead to search for visible passes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (debug output).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    run(
        satcat_id=args.satcat_id,
        user_lat=args.latitude,
        user_lon=args.longitude,
        hours_ahead=args.hours_ahead,
        verbose=args.verbose,
    )
