## satcal

satcal is a small CLI tool for predicting when a given Earth–orbiting satellite will be visible from your location in the next few hours. It pulls orbital data from Celestrak and uses the [Skyfield](https://pypi.org/project/skyfield/) library to compute passes that are both above 20° elevation and actually visible (satellite sunlit, observer in darkness).

### Installation

- **Prerequisites**: Python 3.10+

```bash
pip install satcal
```

or with `uv`:

```bash
uv tool install satcal
```

This installs `satcal` to your path.

### Usage

Once installed, use the `satcal` CLI:

```bash
satcal <satcat_id> <latitude> <longitude> <hours_ahead> [-v|--verbose]
```

- **satcat_id**: NORAD catalog ID (integer) of the satellite.
- **latitude / longitude**: Observer location in decimal degrees.
- **hours_ahead**: How many hours ahead of the current time to search for passes.
- **-v / --verbose** (optional): Enable verbose (debug) logging to stderr.

Example (International Space Station over central London, looking 6 hours ahead):

```bash
satcal 25544 51.501669 -0.141006 6
```

The script will:

- **Sync SATCAT data** from Celestrak into `satcat.csv` (re-downloaded if older than 1 day, or if `FORCE_SYNC_SATCAT=1` is set in the environment).
- Print basic satellite info (name, launch date, and decay date if present) if running verbosely
- **Compute visible passes** using Skyfield and pretty-print a list of passes, each containing:
  - rise / peak / set times (UTC, ISO format)
  - elevation and azimuth in degrees
  - a `visible` flag indicating whether the pass is actually observable (sat sunlit, observer in darkness).

#### Output

The result is printed as a single JSON array on stdout, e.g.

```json
[
  {
    "rise": {
      "time": "2026-03-14T19:35:36Z",
      "alt": 20.004231034654826,
      "az": 220.04202056913311,
      "visible": true
    },
    "peak": {
      "time": "2026-03-14T19:37:37Z",
      "alt": 44.435153007618425,
      "az": 155.68658191565754,
      "visible": true
    },
    "set": {
      "time": "2026-03-14T19:39:37Z",
      "alt": 19.997122770793396,
      "az": 91.46019198197804,
      "visible": false
    }
  }
]
```

- The outer array is one element per visible‑altitude pass found in the requested window.
- Within each pass object:
  - `time` _(string)_: UTC timestamp in ISO 8601 format, e.g. `"2026-03-14T19:37:37Z"`.
  - `alt` _(number)_: altitude in degrees.
  - `az` _(number)_: azimuth in degrees.
  - `visible` _(boolean)_: whether the satellite is sunlit and the observer is in darkness at that moment.

### Notes

- Run with `FORCE_SYNC_SATCAT=1` if you need to force an update.
