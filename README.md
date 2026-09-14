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

Production reads the dedicated Supabase project through `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`. Set these variables in your shell for local development. The runtime needs no service-role key. The migration in `supabase/migrations/` defines private-schema, read-only transit tables and two public, security-invoker RPCs. Each valid search makes one bounded request and returns at most 200 routes; wider matches show a notice asking for a smaller radius. Supabase failures produce a retryable 503 message instead of misleading empty results. Search coordinates are sent in a POST body and are never saved by this app.

The owner-approved import preserves 26 original/local and production file snapshots in the private Supabase Storage bucket `transit-archive`. This includes SQLite, CSV, all JSON properties, fare datasets and both legacy history files. Objects are addressed by SHA-256; the private `transit.archive_manifest` records each original path, size and hash. Every uploaded object was downloaded and verified. The read projection retains 5,044 stops, all 26,043 route records (including text stop-code sentinels), 299 mapped station stops and the original company facts. Original repository files remain as recovery inputs and are excluded from the Vercel function bundle; production does not read them.

Homepage, help, search-form GET and historical facts pages permit one day of Vercel CDN caching. Facts load lazily and are cached per process; no database or dataset reads happen at module import. Personalized POST responses and errors remain private and uncached. There is no polling, refresh cron, automatic dataset collection or history writer. The imported data is historical and does not establish current bus routes or arrival times.

The legacy `/coordinates` page now returns 410 with a privacy notice, and `/static/coordinates.json` returns 404. Existing history remains in the private archive and original recovery files. The production debugger is disabled.

For rollback, promote the previously verified Vercel deployment at commit `4328f8bb84ba6b769d2952452371b3f37c70fbd6`, leaving every Supabase table and archive object intact. That older deployment uses the packaged dataset and restores the older public history behavior, so prefer a forward fix for ordinary issues. Do not drop the archive or projection as part of an application rollback. Future dataset imports need owner review, archive/hash validation and measured Database, Storage, filesystem and egress headroom before any refresh is enabled. Storage has its own allowance; it is not unlimited free capacity.

Search maps use standard OpenStreetMap tiles with visible attribution and ordinary browser caching. The previous CARTO layer returned watermarked tiles without failing the image request, so its error fallback did not activate. Keep map usage within the [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/): interactive viewport requests only, no bulk download or offline prefetch. This community service has no availability guarantee.

Run `python -B -m unittest discover -s tests -v` for search validation, route ordering, missing station mappings, geolocation compatibility and privacy regressions. Tests stub historical-coordinate I/O. GitHub runs these checks on relevant pushes and pull requests. The bundled transit dataset is historical; these checks do not verify current bus schedules or route changes.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
