# SG BusLaoBu


![Project screenshot](./screenshot.png)

A repository for a bus app in Python (Capstone Project)

## Disclaimer:
1. NONE

## Instructions:

1. Download the code as a zip file
2. Extract the files
3. Run the 'main.py' file to start

## Features:
See [criteria.md](criteria.md)

## Grading rubrics:
See [grading.md](grading.md)

## Project Status

sgBusLaoBu2021 project pending fuller documentation and setup notes. This pass standardises repository hygiene without inventing live deployment details or showcase assets.

## Setup

Use Python 3.12 and install the pinned dependencies with `python -m pip install -r requirements.txt`. Start the local app with `python main.py`, or import `main:app` with a WSGI server. Vercel deploys the `master` branch as the Flask app at https://sgbuslaobu.hong-yi.me.

## Usage

Choose a search radius from 0.1 to 1 km and enter coordinates or use browser geolocation. The server checks finite coordinate/radius bounds before querying. Results use forward stop sequences in the packaged route dataset; station entries without a known mapping are skipped.

Bus data remains in the bundled SQLite database and CSV/JSON files. Search connections open SQLite in read-only mode and close after fetching rows. Each search reuses the stop sequences from those rows instead of querying again for each result; station names are cached for the process lifetime. Data-file changes require restarting/redeploying the app.

Normal searches no longer append coordinates to the legacy debug-history files or log the submitted form. Existing history files are retained. Responses containing submitted coordinates use `private, no-store`. The legacy `/coordinates` viewer remains a separate, older feature requiring further review.

Search maps use standard OpenStreetMap tiles with visible attribution and ordinary browser caching. The previous CARTO layer returned watermarked tiles without failing the image request, so its error fallback did not activate. Keep map usage within the [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/): interactive viewport requests only, no bulk download or offline prefetch. This community service has no availability guarantee.

Run `python -B -m unittest discover -s tests -v` for search validation, route ordering, missing station mappings, geolocation compatibility and privacy regressions. Tests stub historical-coordinate I/O. GitHub runs these checks on relevant pushes and pull requests. The bundled transit dataset is historical; these checks do not verify current bus schedules or route changes.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
