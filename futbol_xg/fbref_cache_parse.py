"""Historical offline parser for soccerdata's local FBref HTML cache.

Reads ~/soccerdata/data/FBref and writes data/fbref_team_match.csv. It processes
only locally cached teams; absent pages remain a coverage gap. Cache schema and
collection compatibility were not revalidated for this publication.
"""
import re
from pathlib import Path

import pandas as pd

from ortak import DATA_DIR

FBREF_CACHE = Path.home() / "soccerdata" / "data" / "FBref"
SEZON = "2526"
FBREF_CSV = DATA_DIR / "fbref_team_match.csv"

# FBref matchlog'larındaki 'Comp' değeri -> proje lig anahtarı
COMP_LIG_ESLEME = {
    "Premier League": "ENG-Premier League",
    "La Liga": "ESP-La Liga",
    "Bundesliga": "GER-Bundesliga",
    "Serie A": "ITA-Serie A",
    "Ligue 1": "FRA-Ligue 1",
}


def _matchlog_tablosu_bul(tablolar, cok_baslikli=False):
    """Sayfadaki tablolardan asıl matchlog tablosunu (Date/Comp kolonlu) seçer."""
    for t in tablolar:
        kolonlar = t.columns
        if cok_baslikli:
            alt = [c[1] for c in kolonlar]
        else:
            alt = list(kolonlar)
        if "Date" in alt and "Comp" in alt:
            return t
    return None


def _sut_kolonu(t, alt_ad):
    """Çok başlıklı shooting tablosunda alt-başlığı alt_ad olan ('Standard', 'Sh') gibi
    kolonu döndürür ('For <takım>' grup adı takımdan takıma değiştiği için ada göre arar)."""
    for c in t.columns:
        if c[1] == alt_ad and c[0].startswith("Standard"):
            return t[c]
    for c in t.columns:  # Standard grubu bulunamazsa alt ada göre ilk eşleşme
        if c[1] == alt_ad:
            return t[c]
    raise KeyError(alt_ad)


def takim_schedule_parse(dosya, takim):
    tablolar = pd.read_html(dosya)
    t = _matchlog_tablosu_bul(tablolar)
    if t is None:
        return None

    # Sadece yerel lig maçları (kupa/Avrupa maçlarını at) ve oynanmış maçlar
    t = t[t["Comp"].isin(COMP_LIG_ESLEME)]
    t = t[t["Poss"].notna()]

    return pd.DataFrame({
        "league": t["Comp"].map(COMP_LIG_ESLEME),
        "season": SEZON,
        "team": takim,
        "date": pd.to_datetime(t["Date"]).dt.date,
        "opponent": t["Opponent"],
        "venue": t["Venue"],
        "GF": pd.to_numeric(t["GF"], errors="coerce"),
        "GA": pd.to_numeric(t["GA"], errors="coerce"),
        "possession": pd.to_numeric(t["Poss"], errors="coerce"),
    })


def takim_shooting_parse(dosya, takim):
    tablolar = pd.read_html(dosya, header=[0, 1])
    # 'For <takım>' grubuyla başlayan asıl tablo; 'Against' tablosunu isteme
    aday = None
    for t in tablolar:
        ilk_grup = str(t.columns[0][0])
        alt_adlar = [c[1] for c in t.columns]
        if ilk_grup.startswith("For ") and "Date" in alt_adlar and "Comp" in alt_adlar:
            aday = t
            break
    if aday is None:
        return None

    duz = pd.DataFrame({
        "date": aday[[c for c in aday.columns if c[1] == "Date"][0]],
        "comp": aday[[c for c in aday.columns if c[1] == "Comp"][0]],
        "sut": pd.to_numeric(_sut_kolonu(aday, "Sh"), errors="coerce"),
        "isabetli_sut": pd.to_numeric(_sut_kolonu(aday, "SoT"), errors="coerce"),
    })
    duz = duz[duz["comp"].isin(COMP_LIG_ESLEME)]
    duz = duz[duz["date"].notna()]
    duz["date"] = pd.to_datetime(duz["date"]).dt.date
    duz["team"] = takim
    return duz[["team", "date", "sut", "isabetli_sut"]]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    schedule_dosyalari = sorted(FBREF_CACHE.glob(f"matchlogs_*_{SEZON}_schedule.html"))
    print(f"Önbellekte {len(schedule_dosyalari)} takımın schedule sayfası bulundu.")

    parcalar = []
    sut_parcalari = []
    for sched_dosya in schedule_dosyalari:
        takim = re.match(rf"matchlogs_(.*)_{SEZON}_schedule", sched_dosya.stem).group(1)
        sched = takim_schedule_parse(sched_dosya, takim)
        if sched is None or sched.empty:
            print(f"  UYARI: {takim} schedule parse edilemedi, atlanıyor.")
            continue
        parcalar.append(sched)

        shoot_dosya = FBREF_CACHE / f"matchlogs_{takim}_{SEZON}_shooting.html"
        if shoot_dosya.exists():
            shoot = takim_shooting_parse(shoot_dosya, takim)
            if shoot is not None and not shoot.empty:
                sut_parcalari.append(shoot)
            else:
                print(f"  UYARI: {takim} shooting parse edilemedi, şut kolonları boş kalacak.")
        else:
            print(f"  NOT: {takim} shooting önbellekte yok, şut kolonları boş kalacak.")

    df = pd.concat(parcalar, ignore_index=True)
    sut_df = pd.concat(sut_parcalari, ignore_index=True)
    df = df.merge(sut_df, on=["team", "date"], how="left")

    df.to_csv(FBREF_CSV, index=False)
    print(f"\nKaydedildi: {FBREF_CSV} ({len(df)} satır)")
    print(df.groupby("league").agg(takim=("team", "nunique"), mac=("team", "size"),
                                    sut_dolu=("sut", "count")))


if __name__ == "__main__":
    main()
