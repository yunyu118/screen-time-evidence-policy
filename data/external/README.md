# External search exports

`undermind_refs_metadata.csv` is the reference collection returned by an
independent Undermind deep search, used to measure the recall of this project's
Boolean search (`scripts/06_recall_check.py`). Title, authors, year, journal,
DOI, and citation count are retained. **The abstract column has been removed**:
it is publisher text and not ours to redistribute. Resolve any DOI to read it.

`oa_status.json` records, per DOI, whether an open-access copy exists and where,
via Unpaywall. It is a lookup table, not content.

The recall result is in `data/processed/recall_undermind.json`, and the records
this project's query failed to retrieve are listed in
`data/processed/recall_undermind_missed.csv`.
