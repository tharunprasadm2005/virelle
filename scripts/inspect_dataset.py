import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Inspect the REAL Food.com dataset in data/raw/. Fails clearly if missing."""
import sys
import pandas as pd
from src.data import schema
from src import config


def main():
    try:
        rp, ip = schema.resolve_dataset_files()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(2)
    print(f"Recipe file: {rp}\nInteraction file: {ip}")
    for path in (rp, ip):
        print("=" * 70)
        print(path.name, f"({path.stat().st_size / 1e6:.1f} MB)")
        peek = pd.read_csv(path, nrows=5)
        print("columns:", list(peek.columns))
        print(peek.head(3).to_string())
        # full scan for counts (chunked for large files)
        n, chunks = 0, pd.read_csv(path, chunksize=100_000, usecols=[peek.columns[0]])
        for c in chunks:
            n += len(c)
        print(f"approx rows: {n}")
    print(f"\nDATA_MODE={config.DATA_MODE} (sample = real subset, never synthetic)")


if __name__ == "__main__":
    main()
