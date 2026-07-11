"""Attribution layer: law -> originating bill -> author(s) of record.

Resolves, for each external norm that amends the corpus, the congressional
bill that originated it and its author(s) of record, sourced from Brazilian
Congress open data (Senado Federal "processo" API, with a Câmara dos
Deputados completeness fallback). See `docs/superpowers/plans/2026-07-11-attribution.md`
for the design and `Task 4`'s batch script for how the committed dataset at
`data/attribution/authorship.json` is produced.
"""
