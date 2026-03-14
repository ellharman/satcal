## satcal

satcal is a small CLI tool for predicting when a given Earth–orbiting satellite will be visible from your location in the next few hours. It pulls orbital data from Celestrak and uses the [Skyfield](https://pypi.org/project/skyfield/) library to compute passes that are both above 20° elevation and actually visible (satellite sunlit, observer in darkness).

### Installation

- **Prerequisites**: Python 3.10+

You can install the project in editable mode:

```bash
pip install -e .
```

or, if you use `uv`:

```bash
uv pip install -e .
```

This will also install the required dependencies (`requests`, `requests-cache`, `skyfield`).

### Usage

The main entry point is `main.py` and expects:

```bash
python3 main.py <satcat_id> <latitude> <longitude> <hours_ahead> [log_level]
```

- **satcat_id**: NORAD catalog ID (integer) of the satellite.
- **latitude / longitude**: Observer location in decimal degrees.
- **hours_ahead**: How many hours ahead to search for passes.
- **log_level** (optional): One of `DEBUG`, `INFO`, etc. Defaults to `INFO`.

Example (International Space Station over London, looking 6 hours ahead):

```bash
python3 main.py 25544 51.5074 -0.1278 6
```

The script will:

- **Sync SATCAT data** from Celestrak into `satcat.csv` (re-downloaded if older than 1 day, or if `FORCE_SYNC_SATCAT=1` is set in the environment).
- **Print basic satellite info** (name, launch date, and decay date if present).
- **Compute visible passes** using Skyfield and pretty-print a list of passes, each containing:
  - rise / peak / set times (UTC, ISO format)
  - elevation and azimuth in degrees
  - a `visible` flag indicating whether the pass is actually observable (sat sunlit, observer in darkness).

### Notes

- SATCAT data is considered valid as of 14/03/2026; re-run with `FORCE_SYNC_SATCAT=1` if you need to force an update.
- The observer location can be obtained from any geocoding service (e.g., converting a postcode to latitude/longitude) before calling `main.py`.

