"""Create a curated GitHub upload ZIP with no raw provider inputs or binaries."""
from pathlib import Path
import csv
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parent
ROOT_FILES = ("README.md", "DATA_SOURCES.md", "METHODS.md", "CHANGELOG.md", ".gitignore", ".gitattributes",
              "requirements.txt", "requirements-lock.txt", "requirements-data.txt", "run_analysis.py", "import_inputs.py", "build_upload.py")


def publication_files(root=ROOT):
    paths = [root / name for name in ROOT_FILES]
    paths += list((root / "futbol_xg").glob("*.py")) + list((root / "futbol_xg").glob("*.md"))
    paths += list((root / "futbol").glob("*.py"))
    paths += list((root / "tests").glob("*.py"))
    paths += list((root / ".github" / "workflows").glob("*.yml"))
    for pattern in ("*.png", "*.csv", "*.json"):
        paths += list((root / "results").rglob(pattern))
    synthetic = root / "examples" / "synthetic"
    paths += [synthetic / name for name in ("README.md", "fbref_team_match.csv", "understat_team_match.csv")]
    paths += list((synthetic / "ham_sutlar").glob("*.csv"))
    paths = sorted(set(p for p in paths if p.is_file()))
    for path in paths:
        relative = path.relative_to(root)
        if path.suffix in (".dll", ".pyc", ".lock") or "__pycache__" in relative.parts or ".venv" in relative.parts:
            raise ValueError(f"Unexpected publication artifact: {relative}")
        if relative.parts[:2] == ("futbol_xg", "data"):
            raise ValueError(f"Provider input included: {relative}")
        if relative.as_posix() == "results/xg_reconciliation.csv":
            with path.open(encoding="utf-8", newline="") as handle:
                columns = next(csv.reader(handle))
            if columns != ["league", "season", "game_id", "team", "xg_difference", "within_tolerance"]:
                raise ValueError("Public xG diagnostics must contain only fixture keys, differences and flags")
    return paths


def main():
    output = ROOT.parent / "football-possession-xg-analysis-github.zip"
    paths = publication_files()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026, 10, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    print(f"Created {output} ({len(paths)} files); provider inputs and environment excluded.")


if __name__ == "__main__":
    main()
