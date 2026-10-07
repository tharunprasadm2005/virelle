"""Offline image-liveness audit (resumable, popularity-first).

sndimg rejects HEAD (false 400s), so this issues GET and reads HEADERS ONLY
(body never downloaded). Results: data/processed/image_audit.csv
(recipe_id, image_ok, checked_at). Unchecked ids are treated as unknown
(served legacy-style); checked-dead ones are suppressed by cards.py.

Run: python scripts/audit_images.py --top-n 30000 --workers 20
Resume: re-running skips already-checked ids.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import concurrent.futures
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from src import config


def check(url: str, timeout: int = 10) -> bool:
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200 and (r.headers.get_content_type() or "").startswith("image/")
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=30000)
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()
    df = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv",
                     usecols=["recipe_id", "image_url", "ReviewCount"])
    df = df[df["image_url"].fillna("") != ""].copy()
    df["pop"] = pd.to_numeric(df["ReviewCount"], errors="coerce").fillna(0)
    df = df.sort_values("pop", ascending=False).head(args.top_n)
    out = config.DATA_PROCESSED_DIR / "image_audit.csv"
    done = {}
    if out.exists():
        prev = pd.read_csv(out)
        done = dict(zip(prev["recipe_id"].astype(int), prev["image_ok"].astype(bool)))
    targets = [(int(r), u) for r, u in zip(df["recipe_id"], df["image_url"]) if int(r) not in done]
    print(f"Auditing {len(targets)} urls ({len(done)} already done).")
    rows = [{"recipe_id": k, "image_ok": bool(v),
             "checked_at": datetime.now(timezone.utc).isoformat()} for k, v in done.items()]
    with concurrent.futures.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(check, u): (rid, u) for rid, u in targets}
        for i, fut in enumerate(concurrent.futures.as_completed(futs)):
            rid, _ = futs[fut]
            try:
                ok = bool(fut.result())
            except Exception:
                ok = False
            rows.append({"recipe_id": rid, "image_ok": ok,
                         "checked_at": datetime.now(timezone.utc).isoformat()})
            if (i + 1) % 500 == 0:
                pd.DataFrame(rows).to_csv(out, index=False)
                print(f"  {i+1}/{len(targets)}")
    pd.DataFrame(rows).to_csv(out, index=False)
    ok_n = sum(1 for r in rows if r["image_ok"])
    print(f"Wrote {out}: {ok_n}/{len(rows)} alive.")


if __name__ == "__main__":
    main()
