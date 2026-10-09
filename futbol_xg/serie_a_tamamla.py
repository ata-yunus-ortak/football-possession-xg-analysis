"""Historical optional helper targeting gaps in the 2025-26 FBref cache.

Requests Serie A match logs and Ligue 1 shooting logs for selected teams, then
parses the cache and invokes the validated offline pipeline. Shot-event inputs
must already exist separately. Live collection was not revalidated; success of
a request does not establish complete league coverage. Review the output report.
"""
import subprocess
import sys

from ortak import SCRIPT_DIR



EKSIK_FRA_SHOOTING = ["Rennes", "Strasbourg", "Toulouse"]


def main():
    global sd
    import soccerdata as sd
    from ortak import DATA_DIR
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Serie A matchlog'ları çekiliyor...")
    fb = sd.FBref(leagues=["ITA-Serie A"], seasons=["2526"])
    fb.read_team_match_stats(stat_type="schedule", force_cache=True)
    fb.read_team_match_stats(stat_type="shooting", force_cache=True)
    print("Serie A tamam.")

    print(f"Ligue 1 eksik shooting sayfaları çekiliyor: {EKSIK_FRA_SHOOTING}")
    fb_fra = sd.FBref(leagues=["FRA-Ligue 1"], seasons=["2526"])
    fb_fra.read_team_match_stats(stat_type="shooting", team=EKSIK_FRA_SHOOTING, force_cache=True)
    print("Ligue 1 shooting tamam.")

    print("CSV ve grafikler yeniden üretiliyor...")
    subprocess.run([sys.executable, str(SCRIPT_DIR / "fbref_cache_parse.py")], check=True)
    subprocess.run([sys.executable, str(SCRIPT_DIR.parent / "run_analysis.py")], check=True)
    print("CSV ve analiz çıktıları güncellendi. Kapsam ve dışlamalar için validation_report.json dosyasını inceleyin.")


if __name__ == "__main__":
    main()
