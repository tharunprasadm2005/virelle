"""Offline ingredient index builder (frequency-ordered, resumable).

Strategy (documented): CRF parsing at ~190ms/string cannot cover all 473K unique
Food.com ingredient strings in one session. This script parses the most frequent
unique strings first (top-N covers the majority of recipe mentions) and resumes
across runs. Rule-based normalize.py covers the long tail at read time.

Output: data/processed/ingredient_index.csv + ingredient_index_meta.json
(version stamp: parser name/version, timestamp, coverage, counts).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import ast
import json
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

from src import config
from src.ingredients import normalize as N
from src.ingredients import parser as IP


def unique_by_frequency() -> Counter:
    df = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv", usecols=["ingredients"])
    c = Counter()
    for v in df["ingredients"]:
        try:
            items = ast.literal_eval(v) if isinstance(v, str) else []
        except (ValueError, SyntaxError):
            items = []
        for i in items:
            s = str(i).strip()
            if s:
                c[s.lower()] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=25000)
    ap.add_argument("--resume", action="store_true", default=True)
    args = ap.parse_args()
    out = config.DATA_PROCESSED_DIR / "ingredient_index.csv"
    meta_path = config.DATA_PROCESSED_DIR / "ingredient_index_meta.json"
    done = {}
    if args.resume and out.exists():
        prev = pd.read_csv(out)
        done = dict(zip(prev["raw"].astype(str), prev.index))
        print(f"Resuming: {len(done)} already parsed.")
    freq = unique_by_frequency()
    total_mentions = sum(freq.values())
    targets = [s for s, _ in freq.most_common(args.top_n) if s not in done]
    print(f"Parsing {len(targets)} strings (top-{args.top_n}, {freq and round(sum(freq[s] for s in targets)/total_mentions,3)} mention share this run).")
    rows = []
    if args.resume and out.exists():
        rows = pd.read_csv(out).to_dict(orient="records")
    for i, s in enumerate(targets):
        p = IP.parse_one(s)
        name = N.normalize_name(p["name"] if p["ok"] and p.get("name") else s)
        rows.append({"raw": s, "mentions": int(freq[s]), "name": name,
                     "quantity": p.get("quantity"), "quantity_max": p.get("quantity_max"),
                     "unit": p.get("unit", ""), "preparation": p.get("preparation", ""),
                     "size": p.get("size", ""), "parser_ok": bool(p["ok"]),
                     "confidence": p.get("confidence", 0.0)})
        if (i + 1) % 500 == 0:
            pd.DataFrame(rows).to_csv(out, index=False)
            print(f"  {i+1}/{len(targets)} checkpointed")
    pd.DataFrame(rows).to_csv(out, index=False)
    covered = sum(r["mentions"] for r in rows)
    meta = {"parser": IP.PARSER_NAME, "parser_version": IP.PARSER_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_strings": len(rows), "mention_coverage": round(covered / total_mentions, 4),
            "total_mentions": total_mentions}
    meta_path.write_text(json.dumps(meta, indent=2))
    print("Wrote", out, meta)


if __name__ == "__main__":
    main()
