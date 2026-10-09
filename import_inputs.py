"""Copy existing source CSVs into the ignored local input directory."""
import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Existing project root or its futbol_xg/data directory")
    args = parser.parse_args()
    source = args.source
    if (source / "futbol_xg" / "data").is_dir():
        source = source / "futbol_xg" / "data"
    target = Path(__file__).resolve().parent / "futbol_xg" / "data"
    names = ["fbref_team_match.csv", "understat_team_match.csv"]
    shots = sorted((source / "ham_sutlar").glob("*.csv"))
    if not all((source / name).is_file() for name in names) or not shots:
        parser.error("Expected fbref_team_match.csv, understat_team_match.csv and ham_sutlar/*.csv")
    if source.resolve() == target.resolve():
        parser.error("Source and target must differ")
    target.mkdir(parents=True, exist_ok=True)
    (target / "ham_sutlar").mkdir(exist_ok=True)
    # Refuse partial overwrites: changed datasets deserve a deliberate fresh copy.
    pairs = [(source / n, target / n) for n in names] + [(p, target / "ham_sutlar" / p.name) for p in shots]
    if any(destination.exists() for _, destination in pairs):
        parser.error("Input files already exist; use --data-dir with a different source instead of overwriting")
    for origin, destination in pairs:
        shutil.copy2(origin, destination)
    print(f"Imported {len(pairs)} source files into {target}")


if __name__ == "__main__":
    main()
