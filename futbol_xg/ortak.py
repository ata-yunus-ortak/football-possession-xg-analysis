"""Side-effect-free project paths and source-name mappings."""
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
CIKTI_DIR = SCRIPT_DIR / "cikti"
SEZONLAR = ["2526"]
LIG_ADLARI = {"ENG-Premier League": "Premier League", "ESP-La Liga": "La Liga", "GER-Bundesliga": "Bundesliga", "ITA-Serie A": "Serie A", "FRA-Ligue 1": "Ligue 1"}
LIGLER = list(LIG_ADLARI)
TAKIM_ISIM_ESLEME = {
 "Manchester Utd": "Manchester United", "Newcastle": "Newcastle United", "Nottingham": "Nottingham Forest", "Wolves": "Wolverhampton Wanderers",
 "Leicester City": "Leicester", "Ipswich Town": "Ipswich", "Leeds United": "Leeds", "Alavés": "Alaves", "Atlético Madrid": "Atletico Madrid", "Oviedo": "Real Oviedo",
 "Dortmund": "Borussia Dortmund", "Frankfurt": "Eintracht Frankfurt", "Gladbach": "Borussia M.Gladbach", "Heidenheim": "FC Heidenheim", "Köln": "FC Cologne",
 "Leverkusen": "Bayer Leverkusen", "RB Leipzig": "RasenBallsport Leipzig", "St Pauli": "St. Pauli", "Stuttgart": "VfB Stuttgart", "PSG": "Paris Saint Germain",
}
