"""Offline validation and statistics. No scraper or plotting dependency."""
import numpy as np
import pandas as pd
from ortak import TAKIM_ISIM_ESLEME

STATES = ("leading", "drawing", "trailing")
STATE_LABELS = dict(zip(STATES, ("Leading", "Drawing", "Trailing")))
BIN_LABELS = [f"{n}-{n + 4}%" for n in range(25, 70, 5)] + ["70-75%"]


def require_columns(frame, names, source):
    missing = set(names) - set(frame.columns)
    if missing:
        raise ValueError(f"{source}: missing columns {sorted(missing)}")


def require_unique(frame, keys, source):
    if frame.duplicated(keys).any():
        raise ValueError(f"{source}: duplicate keys {keys}")


def merge_sources(fbref, understat):
    require_columns(fbref, ["league", "season", "team", "opponent", "venue", "GF", "possession", "sut"], "FBref")
    require_columns(understat, ["league", "season", "team", "opponent", "venue", "game_id", "gol", "xg"], "Understat")
    keys = ["league", "season", "team", "opponent", "venue"]
    f = fbref.copy()
    f["team"] = f.team.replace(TAKIM_ISIM_ESLEME)
    f["opponent"] = f.opponent.replace(TAKIM_ISIM_ESLEME)
    require_unique(f, keys, "FBref")
    require_unique(understat, keys, "Understat")
    require_unique(understat, ["league", "season", "game_id", "team"], "Understat")
    merged = f.merge(understat[keys + ["game_id", "gol", "xg"]], on=keys,
                     how="left", validate="one_to_one", indicator=True)
    matched = merged._merge == "both"
    for column in ("GF", "gol"):
        values = merged.loc[matched, column]
        if not np.isfinite(values).all() or (values < 0).any() or (values % 1 != 0).any():
            raise ValueError("Final goals must be finite, non-negative whole numbers")
    if (merged.loc[matched, "GF"] != merged.loc[matched, "gol"]).any():
        raise ValueError("FBref and Understat goal totals disagree on matched fixtures")
    if not merged.possession.between(0, 100).all():
        raise ValueError("Possession must be numeric and between 0 and 100")
    for column in ("sut", "xg"):
        values = merged[column].dropna()
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Shot counts and xG must be finite and non-negative when provided")
    if (merged.sut.dropna() % 1 != 0).any():
        raise ValueError("Shot counts must be whole numbers when provided")
    coverage = {
        "fbref_rows": len(f), "understat_rows": len(understat),
        "matched_rows": int(matched.sum()), "unmatched_fbref_rows": int((~matched).sum()),
        "missing_fbref_shots": int(f.sut.isna().sum()),
        "missing_understat_xg": int(understat.xg.isna().sum()),
        "possession_leagues": sorted(merged.loc[matched, "league"].unique()),
        "missing_possession_leagues": sorted(set(understat.league) - set(f.league)),
    }
    if not matched.all():
        raise ValueError(f"{coverage['unmatched_fbref_rows']} FBref fixtures failed to match; update name mappings")
    return merged.drop(columns="_merge"), coverage


def possession_dilimle(frame, possession_kolonu="possession"):
    """Analysis range [25, 75], including the final endpoint consistently."""
    d = frame.loc[frame[possession_kolonu].between(25, 75)].copy()
    edges = list(range(25, 75, 5)) + [np.nextafter(75.0, np.inf)]
    d["Possession_Bin"] = pd.cut(d[possession_kolonu], edges, labels=BIN_LABELS, right=False)
    return d


def possession_statistics(frame, metric, repetitions=1000, seed=2026):
    """95% percentile intervals with match clusters inside each bin.

    These are descriptive within-bin intervals, not causal or between-bin tests.
    """
    if metric not in ("shot_quality", "finishing", "volume"):
        raise ValueError(f"Unknown metric {metric}")
    d = possession_dilimle(frame)
    required = ["xg", "sut"] if metric == "shot_quality" else ["xg", "gol"] if metric == "finishing" else ["xg"]
    d = d.dropna(subset=required)
    rng = np.random.default_rng(seed)
    rows = []
    for label, group in d.groupby("Possession_Bin", observed=True, sort=True):
        group = group.copy()
        group["numerator"] = group.gol - group.xg if metric == "finishing" else group.xg
        group["denominator"] = group.sut if metric == "shot_quality" else 1.0
        clusters = group.groupby(["league", "season", "game_id"])[["numerator", "denominator"]].sum()
        num, den = clusters.numerator.to_numpy(), clusters.denominator.to_numpy()
        total_den = den.sum()
        estimate = num.sum() / total_den if total_den else np.nan
        lo, hi = np.nan, np.nan
        if len(clusters) > 1 and repetitions:
            indices = rng.integers(0, len(clusters), size=(repetitions, len(clusters)))
            denominators = den[indices].sum(axis=1)
            samples = np.divide(num[indices].sum(axis=1), denominators,
                                out=np.full(repetitions, np.nan), where=denominators > 0)
            finite = samples[np.isfinite(samples)]
            if len(finite):
                lo, hi = np.quantile(finite, [0.025, 0.975])
        rows.append({"Possession_Bin": str(label), "value": estimate, "ci_low": lo, "ci_high": hi,
                     "n": len(group), "match_clusters": len(clusters)})
    return pd.DataFrame(rows, columns=["Possession_Bin", "value", "ci_low", "ci_high", "n", "match_clusters"])


def _state(score_for, score_against):
    return "leading" if score_for > score_against else "trailing" if score_for < score_against else "drawing"


def reconstruct_game_states(shots, fixtures, durations=None, exclude_score_mismatches=False):
    """Replay scores; own goals are not attacking shots.

    Optional duration schema: league, season, game_id, end_minute, using the
    event clock. Absent end times are explicitly estimated, never verified.
    """
    require_columns(shots, ["league", "season", "game_id", "shot_id", "team", "minute", "xg", "result"], "Shots")
    require_columns(fixtures, ["league", "season", "game_id", "team", "opponent", "venue", "gol"], "Fixtures")
    key = ["league", "season", "game_id"]
    require_unique(shots, ["league", "season", "shot_id"], "Shots")
    require_unique(fixtures, key + ["team"], "Fixtures")
    if not np.isfinite(fixtures.gol).all() or (fixtures.gol < 0).any() or (fixtures.gol % 1 != 0).any():
        raise ValueError("Final goals must be finite, non-negative whole numbers")
    if not np.isfinite(shots[["minute", "xg"]]).all().all() or (shots.minute < 0).any() or (shots.xg < 0).any():
        raise ValueError("Events need finite, non-negative minute and xG values")
    known_results = {"Goal", "Own Goal", "Missed Shot", "Blocked Shot", "Saved Shot", "Shot On Post"}
    if not set(shots.result).issubset(known_results):
        raise ValueError("Unknown event result; review the source schema")
    ends = {}
    if durations is not None:
        require_columns(durations, key + ["end_minute"], "Durations")
        require_unique(durations, key, "Durations")
        if not np.isfinite(durations.end_minute).all() or (durations.end_minute <= 0).any():
            raise ValueError("Match end minutes must be finite and positive")
        ends = durations.set_index(key).end_minute.to_dict()
    fixture_groups = {k: g for k, g in fixtures.groupby(key)}
    shot_rows, exposure_rows, reconciliation = [], [], []
    observed = set()
    for match_key, events in shots.groupby(key, sort=True):
        if match_key not in fixture_groups:
            raise ValueError(f"Missing fixture for {match_key}")
        fixture = fixture_groups[match_key]
        h = fixture.loc[fixture.venue == "Home"]
        a = fixture.loc[fixture.venue == "Away"]
        if len(h) != 1 or len(a) != 1 or h.iloc[0].opponent != a.iloc[0].team or a.iloc[0].opponent != h.iloc[0].team:
            raise ValueError(f"Invalid home/away fixture pair for {match_key}")
        home, away = h.iloc[0].team, a.iloc[0].team
        if not set(events.team).issubset({home, away}):
            raise ValueError(f"Unexpected event team in {match_key}")
        events = events.sort_values("minute", kind="stable")
        last_minute = float(events.minute.max())
        verified = match_key in ends
        end = float(ends[match_key]) if verified else max(90.0, last_minute + 1.0)
        if end < last_minute:
            raise ValueError(f"Match end precedes its last event in {match_key}")
        score = {home: 0, away: 0}
        exposure = {t: dict.fromkeys(STATES, 0.0) for t in (home, away)}
        match_shots, match_exposure = [], []
        previous = 0.0
        for event in events.itertuples():
            minute = float(event.minute)
            for team, opponent in ((home, away), (away, home)):
                exposure[team][_state(score[team], score[opponent])] += minute - previous
            previous = minute
            opponent = away if event.team == home else home
            match_shots.append({"league": match_key[0], "season": match_key[1], "game_id": match_key[2],
                              "shot_id": event.shot_id, "team": event.team, "minute": minute,
                              "xg": float(event.xg), "result": event.result,
                              "durum": _state(score[event.team], score[opponent]),
                              "is_attacking_shot": event.result != "Own Goal"})
            if event.result == "Goal":
                score[event.team] += 1
            elif event.result == "Own Goal":
                score[opponent] += 1
        for team, opponent in ((home, away), (away, home)):
            exposure[team][_state(score[team], score[opponent])] += end - previous
            for state in STATES:
                match_exposure.append({"league": match_key[0], "season": match_key[1], "game_id": match_key[2],
                                      "team": team, "durum": state, "minutes": exposure[team][state],
                                      "duration_source": "provided" if verified else "estimated"})
        expected_scores = {team: int(fixture.loc[fixture.team == team, "gol"].iloc[0]) for team in (home, away)}
        verified_score = score == expected_scores
        if not verified_score and not exclude_score_mismatches:
            raise ValueError(f"Replayed score mismatch for {match_key}: {score} != {expected_scores}")
        if verified_score:
            shot_rows.extend(match_shots)
            exposure_rows.extend(match_exposure)
        reconciliation.append({"league": match_key[0], "season": match_key[1], "game_id": match_key[2],
                               "score_verified": verified_score, "end_minute": end,
                               "replayed_score": f"{score[home]}-{score[away]}",
                               "fixture_score": f"{expected_scores[home]}-{expected_scores[away]}",
                               "excluded_events": 0 if verified_score else len(events),
                               "duration_source": "provided" if verified else "estimated",
                               "same_minute_multi_events": int(events.minute.duplicated(keep=False).sum())})
        observed.add(match_key)
    if not shot_rows:
        raise ValueError("No shot events to analyse")
    missing = sorted(set(fixture_groups) - observed)
    return (pd.DataFrame(shot_rows), pd.DataFrame(exposure_rows), pd.DataFrame(reconciliation),
            [{"league": k[0], "season": int(k[1]), "game_id": int(k[2])} for k in missing])


def summarize_states(events, exposure):
    keys = ["league", "season", "team", "durum"]
    attacks = events.loc[events.is_attacking_shot].copy()
    attacks["goal"] = (attacks.result == "Goal").astype(int)
    shot_summary = attacks.groupby(keys).agg(toplam_xg=("xg", "sum"), toplam_sut=("shot_id", "count"), toplam_gol=("goal", "sum")).reset_index()
    minutes = exposure.groupby(keys).agg(toplam_dakika=("minutes", "sum"),
                                        estimated_duration=("duration_source", lambda s: (s == "estimated").any())).reset_index()
    summary = minutes.merge(shot_summary, on=keys, how="left", validate="one_to_one")
    summary[["toplam_xg", "toplam_sut", "toplam_gol"]] = summary[["toplam_xg", "toplam_sut", "toplam_gol"]].fillna(0)
    for output, numerator, denominator, scale in (("xg_90", "toplam_xg", "toplam_dakika", 90),
                                                  ("xg_sut_basina", "toplam_xg", "toplam_sut", 1),
                                                  ("donusum", "toplam_gol", "toplam_xg", 1)):
        summary[output] = summary[numerator].div(summary[denominator].replace(0, np.nan)) * scale
    return summary


def reconcile_xg(events, fixtures, tolerance=0.001):
    """Audit summed attacking-shot xG against fixture xG without editing events.

    Fixture aggregates may use a different definition from the sum of shot xG.
    A discrepancy is reported, not treated as proof of corrupt events. Only
    fixtures retained after score replay are included; zero-shot teams get 0.
    """
    keys = ["league", "season", "game_id", "team"]
    require_columns(fixtures, keys + ["xg"], "Fixtures")
    require_unique(fixtures, keys, "Fixtures")
    included = events[keys[:3]].drop_duplicates()
    rows = fixtures.merge(included, on=keys[:3], how="inner", validate="many_to_one")
    rows = rows[keys + ["xg"]].rename(columns={"xg": "fixture_xg"})
    attacks = events.loc[events.is_attacking_shot]
    totals = attacks.groupby(keys).agg(event_xg=("xg", "sum"), attacking_shots=("shot_id", "count")).reset_index()
    result = rows.merge(totals, on=keys, how="left", validate="one_to_one")
    result[["event_xg", "attacking_shots"]] = result[["event_xg", "attacking_shots"]].fillna(0)
    result["attacking_shots"] = result.attacking_shots.astype(int)
    result["xg_difference"] = result.event_xg - result.fixture_xg
    result["within_tolerance"] = result.xg_difference.abs().le(tolerance).where(result.fixture_xg.notna())
    return result.sort_values(keys).reset_index(drop=True)


def audit_event_order(events, fixtures):
    """Compare minute replay with numeric-ID order as an unverified sensitivity.

    Numeric IDs are not a verified chronology. This diagnostic never rewrites
    the event labels or exposure; it shows why final-score agreement alone is
    insufficient to establish each event's score state.
    """
    keys = ["league", "season", "game_id"]
    rows = []
    for match_key, group in events.groupby(keys, sort=True):
        group = group.assign(numeric_id=pd.to_numeric(group.shot_id, errors="coerce"))
        available = group.numeric_id.notna().all()
        row = dict(zip(keys, match_key))
        row.update(numeric_id_order_available=bool(available), minute_decreases=0,
                   scoring_minute_decreases=0, alternative_state_labels=0)
        if available:
            ordered = group.sort_values("numeric_id", kind="stable")
            decreases = ordered.minute.diff().lt(0)
            scoring = ordered.result.isin(["Goal", "Own Goal"])
            row["minute_decreases"] = int(decreases.sum())
            row["scoring_minute_decreases"] = int((decreases & (scoring | scoring.shift(fill_value=False))).sum())
            fixture = fixtures.loc[(fixtures[keys] == pd.Series(dict(zip(keys, match_key)))).all(axis=1)]
            home = fixture.loc[fixture.venue == "Home", "team"].iloc[0]
            away = fixture.loc[fixture.venue == "Away", "team"].iloc[0]
            score = {home: 0, away: 0}
            for event in ordered.itertuples():
                opponent = away if event.team == home else home
                row["alternative_state_labels"] += int(_state(score[event.team], score[opponent]) != event.durum)
                if event.result == "Goal":
                    score[event.team] += 1
                elif event.result == "Own Goal":
                    score[opponent] += 1
        rows.append(row)
    return pd.DataFrame(rows)
