# Preparation changes — 8 October 2026

- Corrected own-goal attribution and excluded own-goal records from attacking-shot metrics.
- Added final-score reconciliation; quarantined one inconsistent fixture instead of silently removing repeated-looking records.
- Corrected paired-complete xG/shot aggregation and included the 75% possession endpoint.
- Rebuilt game-state tables, preserving exposure for zero-shot states and grouping by season.
- Added optional match-duration inputs and explicit estimated-exposure labels.
- Replaced truncated bar comparisons with shared scales and bootstrap intervals for possession estimates.
- Corrected four-league possession coverage, English figure labels and claims of statistical independence/causal mechanisms.
- Added an offline entry point, source checksums, validation reports, synthetic regression tests and a fresh-clone demo.
- Added pinned offline dependencies and separate optional collection dependencies. Removed machine-specific DLL requirements from analysis imports.
- Isolated earlier possession/goals exploration and corrected its league labels and working-directory dependence.
- Added Git exclusions and a curated upload archive; raw provider inputs and local environment files remain outside the archive.

The initial source workspace remains available separately. Preparation fixes and published outputs are in this repository directory.

## Portfolio review — 10 October 2026

- Added author attribution, a concise case-study narrative and compact overview charts generated from the existing aggregate results.
- Linked full league-level figures and machine-readable summaries from the front page.
- Clarified that duration inputs are user-provided and corrected historical collection descriptions; the offline state builder does not download events.
- Added fixture-versus-event xG reconciliation with full derived diagnostics, including zero-shot teams. Documented aggregate differences separately from final-score verification; retained events and the existing whole-fixture score exclusions.
- Kept detailed per-team xG values local-only; public diagnostics contain fixture keys, differences and flags. The upload builder verifies this column boundary.
- Added an explicitly unverified numeric-ID ordering sensitivity and prominent chronology limitations for exploratory score-state results.
- Rejected fractional final scores, fractional shot counts and non-finite metric values; added regression cases for these validator gaps.
