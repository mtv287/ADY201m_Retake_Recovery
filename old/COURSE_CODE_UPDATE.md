# Course Code Update

All processed datasets now use decoded course codes in the `course_id` column instead of temporary proxies `C01`-`C18`.

## Mapping

| Proxy | Decoded course code |
|---|---|
| C01 | ADY201M |
| C02 | PCP291 |
| C03 | PRJ301 |
| C04 | PRF193 |
| C05 | PFP191 |
| C06 | PRJ321 |
| C07 | DAP391M |
| C08 | CSD201 |
| C09 | IOT101 |
| C10 | CSD203 |
| C11 | PRO192 |
| C12 | IOT102 |
| C13 | PRJ30X |
| C14 | LAB211 |
| C15 | OSG202 |
| C16 | CEA201 |
| C17 | DBI202 |
| C18 | PRF192 |

## What was changed

- `master_raw.csv`
- `master_sql_ready.csv`
- `clean_attempts_v1.csv`
- duplicate review CSVs
- `retake_pairs_v1.csv` and TV3 manual sample
- `course_map.csv`
- TV1 integration notebook (future reruns now generate decoded course codes)
- documentation that previously described `C01-C18` as temporary course IDs

The raw source CSV files were not modified. Student IDs and class IDs were not changed.
