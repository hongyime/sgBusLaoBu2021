# SG Bus LaoBu maintenance state

2026-09-14: Owner approved production migration to the dedicated Bus Supabase project, with all records preserved and no paid upgrade.

The private archive import preserves 26 original and production file snapshots, verified by downloading every object and comparing SHA-256. This includes all transit formats, fare files and both legacy history files. The read projection contains 5,044 stops, 26,043 route records and 299 mapped station stops. SQLite's INTEGER-declared stop-code column includes text sentinels; the projection preserves these as text. Full projection equality and eight search comparisons with the former implementation passed, including exact stored floating-point bytes and a maximum-200 result notice.

The runtime now uses one bounded Supabase RPC per valid search, no local data reads at import, lazy cached facts and one-day public page caching. It does not collect coordinates. Legacy history URLs no longer expose records. The original dirty checkout and all data/env hashes remain unchanged.

Release PR #80 is in validation. Application/security checks passed, and Vercel built the migration preview successfully. Fixed the pre-existing Labeler configuration format rejected by its current Action. Confirm the final GitHub checks, Vercel source revision, cache behavior and a targeted real search before calling the cutover complete. Keep the private archive and database intact during any application rollback. Do not add scheduled collection or refresh without capacity review. Monthly CPU and egress savings remain unmeasured.
