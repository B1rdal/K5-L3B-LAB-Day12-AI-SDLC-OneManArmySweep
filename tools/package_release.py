"""Create the reproducible local v1.0.0 release archive."""

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "Chonoi-v1.0.0.zip"
EXCLUDED_PARTS = {".git", ".pytest_cache", "__pycache__", "dist"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return not (set(relative.parts) & EXCLUDED_PARTS or path.suffix in EXCLUDED_SUFFIXES)


def main() -> int:
    OUTPUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and included(path):
                target = Path("Chonoi-v1.0.0") / path.relative_to(ROOT)
                archive.write(path, target.as_posix())
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
