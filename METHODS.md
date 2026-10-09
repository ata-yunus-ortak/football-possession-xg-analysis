# Methods and interpretation

## Matching and coverage

FBref team names are normalized to Understat names. Fixtures are matched on league, season, team, opponent and home/away venue, with a one-to-one merge and a final-goal check. This is appropriate for the supplied double-round-robin league snapshot; a different competition format needs a fixture-ID adapter. Failed matches are errors rather than silently dropped observations.

## Possession metrics

The selected range is **25–75%, inclusive**. It is an analysis-scope choice, not an assertion that observations outside that range are incorrect. Five-percentage-point intervals are left-closed; the final interval includes 75. Integer-percentage labels describe this snapshot; continuous percentages still follow the same numerical edges.

- **Chance volume:** mean Understat xG per complete team-match.
- **Shot quality:** sum of Understat xG / sum of FBref shot counts, using the same paired-complete rows for both numerator and denominator. It is a ratio of sums, not the unweighted mean of per-match ratios. Cross-provider shot definitions may differ.
- **Finishing residual:** mean (non-adjusted final team goals − xG) per complete team-match. Final goals include own goals awarded to that team; this is distinct from the non-own-goal conversion metric below.

Intervals use 1,000 seeded percentile bootstrap samples, grouping the observations of the same league/season/game inside each possession bin. They do not control for team strength, score state, opposition or match time, and they do not establish independence or causation. Missing observations may be non-random. One season does not establish generalisation across seasons.

## Fixture xG versus summed shot xG

Possession estimates use Understat **fixture-summary xG**. Score-state estimates use the **sum of individual attacking-shot xG**. They are distinct quantities in this snapshot. A local-only reconciliation table beside the inputs retains both values and their signed difference for every team in a score-verified fixture, including zero-shot teams. Missing fixture xG stays missing. The public `xg_reconciliation.csv` retains only fixture identifiers, the derived difference and a tolerance flag; it does not republish individual fixture or shot-sum xG values.

An absolute diagnostic tolerance of 0.001 flags differences above rounding scale; it is not a significance test or a provider-specified guarantee. In the current sample, 1,400 of 3,500 team-match rows across 1,135 fixtures exceed this tolerance. Shot xG sums total 5,417.1062; fixture xG totals 5,326.3136. Provider aggregate definitions may differ, but no grouping rule is verified here. Discrepancies are reported without rescaling xG, deleting shots or automatically excluding additional fixtures.

## Score replay

Events are sorted by minute with stable source ordering for ties. A shot is labelled with the score **before** its outcome. A Goal increments its own team; an Own Goal increments its opponent. Own-goal events remain in the event audit but are excluded from attacking-shot count, attacking xG and non-own-goal conversion.

Replayed final scores must match fixture summaries. The default core API raises on mismatch. The case-study pipeline instead quarantines whole mismatched fixtures and records their identifiers and discrepancies. It never tries to guess which duplicate-looking event to keep. A fixture with no events is listed separately and receives no invented minutes or shots.

The minute-level source cannot establish the true order of multiple events within the same integer minute. It also lacks period, a precise timestamp and the original clock string, so possible overlap between first-half stoppage time and second-half minutes cannot be repaired from these files. Stable minute sorting is reproducible, not evidence of exact timing. Final-score agreement does not validate intermediate score states.

`event_order_diagnostics.csv` compares this replay with numeric shot-ID order as an **unverified sensitivity**, never a replacement chronology. Among the 1,750 included fixtures, 258 have a decrease in minute when sorted by numeric ID; 67 decreasing adjacencies involve a Goal/Own Goal on either side. An ID-order replay changes 378 pre-shot labels in 287 fixtures. ID chronology itself is undocumented, so these counts expose sensitivity without identifying which ordering is true. Score-state comparisons and exposure rates are exploratory.

## Exposure and zero-shot states

Every included fixture contributes all three states for both teams, including states with zero minutes or shots. Exposure summaries are the left side of the merge so zero-shot minutes remain present. League, season, team and state are all grouping keys.

If no duration is supplied, the modelled end is `max(90, last_event_minute + 1)`. The extra minute avoids ending an interval at the start of the last integer minute; it does not recover the true whistle time. This estimate differs from the earlier `max(90, last_event_minute)` convention and is labelled in every exposure-based result.

An optional end-time file can replace estimates for selected matches. Its clock must be consistent with the event minutes. A provided value earlier than the last event is rejected. Time zero, stoppage-time encoding and finite minute resolution still depend on the source.

- **xG per attacking shot:** attacking xG / attacking-shot count.
- **Conversion:** non-own-goal goals / attacking xG.
- **Approximate xG/90:** attacking xG / modelled state minutes × 90.

Zero denominators produce missing ratios rather than infinity. Zero xG over positive exposure produces zero xG/90.

## Presentation

Possession estimates are point/interval plots. Non-negative bar metrics start at zero; panel scales are shared. Signed goals-minus-xG plots include zero. Sample labels specify team-match observations or attacking shots. Missing leagues and exclusions are visible rather than described as complete five-league coverage.
