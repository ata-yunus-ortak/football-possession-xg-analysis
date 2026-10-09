"""Historical optional collector for FBref and Understat team-match tables.

This utility does not collect shot events. Supply event CSVs separately under
data/ham_sutlar/; oyun_durumu_hesapla.py reads and validates those files offline.
Live collection was not revalidated for this publication.
"""
import pandas as pd

from ortak import DATA_DIR, LIGLER, SEZONLAR



FBREF_CSV = DATA_DIR / "fbref_team_match.csv"
UNDERSTAT_CSV = DATA_DIR / "understat_team_match.csv"


def _fbref_lig_cek(lig, sezonlar):
    """Tek bir ligi ayrı bir FBref oturumuyla çeker.

    soccerdata'nın FBref(leagues=[...]) çoklu-lig modu, bazı liglerin index'ini
    NaN'a çeviren tekrarlanabilir bir concat bug'ına sahip (görüldü: 5 ligi birden
    çekince Bundesliga+Serie A satırları 'league' kolonunda NaN olarak geliyor ve
    satır sayısı ikiye katlanıyor). Her ligi kendi FBref() örneğiyle ayrı çekmek
    bu bug'ı bypass ediyor.
    """
    fb = sd.FBref(leagues=[lig], seasons=sezonlar)

    sched = fb.read_team_match_stats(stat_type="schedule", force_cache=True)
    temel = pd.DataFrame({
        "league": lig,
        "season": sched.index.get_level_values("season"),
        "team": sched.index.get_level_values("team"),
        "game": sched.index.get_level_values("game"),
        "date": sched["date"].values,
        "opponent": sched["opponent"].values,
        "venue": sched["venue"].values,
        "GF": sched["GF"].values,
        "GA": sched["GA"].values,
        "possession": sched["Poss"].values,
    })

    try:
        shoot = fb.read_team_match_stats(stat_type="shooting", force_cache=True)
        sut = pd.DataFrame({
            "league": lig,
            "season": shoot.index.get_level_values("season"),
            "team": shoot.index.get_level_values("team"),
            "game": shoot.index.get_level_values("game"),
            "sut": shoot[("Standard", "Sh")].values,
            "isabetli_sut": shoot[("Standard", "SoT")].values,
        })
        return temel.merge(sut, on=["league", "season", "team", "game"], how="left")
    except Exception as hata:
        print(f"UYARI: {lig} için şut (shooting) verisi çekilemedi ({hata!r}). "
              f"Possession verisi kaydediliyor, 'sut'/'isabetli_sut' bu lig için boş bırakılıyor; "
              f"veri_cek.py'yi daha sonra tekrar çalıştırıp tamamlanabilir.")
        return temel.assign(sut=pd.NA, isabetli_sut=pd.NA)


def fbref_verisi_cek(ligler, sezonlar):
    parcalar = []
    for lig in ligler:
        print(f"  {lig} çekiliyor...")
        parcalar.append(_fbref_lig_cek(lig, sezonlar))
    return pd.concat(parcalar, ignore_index=True)


def understat_verisi_cek(ligler, sezonlar):
    us = sd.Understat(leagues=ligler, seasons=sezonlar)
    sched = us.read_schedule()

    ortak_kolonlar = {
        "league": sched.index.get_level_values("league"),
        "season": sched.index.get_level_values("season"),
        "game_id": sched["game_id"].values,
        "date": sched["date"].values,
    }
    ev = pd.DataFrame({
        **ortak_kolonlar,
        "team": sched["home_team"].values,
        "opponent": sched["away_team"].values,
        "venue": "Home",
        "gol": sched["home_goals"].values,
        "xg": sched["home_xg"].values,
    })
    deplasman = pd.DataFrame({
        **ortak_kolonlar,
        "team": sched["away_team"].values,
        "opponent": sched["home_team"].values,
        "venue": "Away",
        "gol": sched["away_goals"].values,
        "xg": sched["away_xg"].values,
    })
    return pd.concat([ev, deplasman], ignore_index=True)


def main():
    global sd
    import soccerdata as sd
    from ortak import DATA_DIR
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if FBREF_CSV.exists():
        print(f"{FBREF_CSV.name} zaten var, atlanıyor (silip tekrar çalıştırabilirsin).")
    else:
        print(f"FBref verisi çekiliyor: {len(LIGLER)} lig x {len(SEZONLAR)} sezon...")
        fbref_df = fbref_verisi_cek(LIGLER, SEZONLAR)
        fbref_df.to_csv(FBREF_CSV, index=False)
        print(f"Kaydedildi: {FBREF_CSV} ({len(fbref_df)} satır)")

    if UNDERSTAT_CSV.exists():
        print(f"{UNDERSTAT_CSV.name} zaten var, atlanıyor (silip tekrar çalıştırabilirsin).")
    else:
        print(f"Understat verisi çekiliyor: {len(LIGLER)} lig x {len(SEZONLAR)} sezon...")
        understat_df = understat_verisi_cek(LIGLER, SEZONLAR)
        understat_df.to_csv(UNDERSTAT_CSV, index=False)
        print(f"Kaydedildi: {UNDERSTAT_CSV} ({len(understat_df)} satır)")


if __name__ == "__main__":
    main()
