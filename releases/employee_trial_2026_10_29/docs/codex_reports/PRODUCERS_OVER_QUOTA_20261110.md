# Producers Over Quota Report — initial review superseded

The complete legacy CSV supplied in the parity follow-up supersedes the initial
filtered-PDF interpretation. The report lists **all producers with positive
confirmed quota**, including those at or below 100%. Only over-quota Account
Total percentage cells are red. There is no longer a greater-than-100% account
inclusion filter.

See [PRODUCERS_OVER_QUOTA_PARITY_20261110.md](PRODUCERS_OVER_QUOTA_PARITY_20261110.md)
for the current specification, fixture provenance, exact source-data gaps,
future-flock inventory and date comparisons, and regression coverage.

The earlier three-page PDF contains 32 flock rows and 16 Account Totals; it is a
partial output reference, not evidence of the full population. The newly supplied
CSV contains 47 flock rows across 24 producers. The original PDF fixture is kept
unchanged for partial projection regression tests.

Inventory, whole-week age, monthly mortality, Count/Delivery selection, future
placement zeroes and the confirmed Egg Production quota basis still use existing
shared builders. Last Count remains blank for Delivery fallback and future
placements. Dates remain DD/MM/YYYY. CSV/XLSX contain the original result data;
red UI/PDF formatting does not add columns or change values. No SQL was added.

The newer local DEV report export supplies observations for most previously
missing source-calculation checks, including Cornwallis. Its evidence limits and
remaining absent 40407 source row are documented in the parity report. No Count
quantity or Hatch Date was reverse-solved or fabricated.
