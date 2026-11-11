"""Build summary.csv (+ a per-run histogram json) from EvaLoop result files.

Usage:
  python scripts/make_summary.py --out summary.csv \
      --run MODEL CONFIG PATH_TO_EVALOOP_RESULTS.json [--run ...] \
      [--baseline MODEL CONFIG PATH_TO_DATAPACKAGE_LOOP.json ...]

``--run`` reads files written by ``evaloop evaluate`` (list with one dict, key prompt_results).
``--baseline`` reads data-package loop files (key tasks); only the numbers are used, nothing copied.
asl_score is the quadratic ASL without semantic weighting, sum_i n_i i^2 / (T*M)
(evaloop.analysis.metrics.asl_pow); it equals the leaderboard's aslScore column in the data package
before similarity weighting. No LLM judge is used.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from evaloop.analysis.metrics import asl_pow, cycle_histogram, pass_at_k  # noqa: E402


def stats(cycles, max_cycles=10):
    T = len(cycles)
    return {
        "n_tasks": T,
        "success_rate": pass_at_k(cycles, 1) / T,
        "asl_score": asl_pow(cycles, max_cycles),
        "histogram": cycle_histogram(cycles, max_cycles),
        "pass_at_10": pass_at_k(cycles, max_cycles) / T,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="summary.csv")
    ap.add_argument("--run", nargs=3, action="append", default=[], metavar=("MODEL", "CONFIG", "PATH"))
    ap.add_argument("--baseline", nargs=3, action="append", default=[], metavar=("MODEL", "CONFIG", "PATH"))
    a = ap.parse_args()
    rows, extra = [], []
    for model, conf, path in a.baseline:
        d = json.load(open(path, encoding="utf8"))
        s = stats([t["successful_cycles"] for t in d["tasks"]])
        rows.append((model, conf, s)); extra.append((model, conf, s))
    for model, conf, path in a.run:
        d = json.load(open(path, encoding="utf8"))
        d = d[0] if isinstance(d, list) else d
        s = stats([r["successful_cycles"] for r in d["prompt_results"]], d.get("max_cycles", 10))
        rows.append((model, conf, s)); extra.append((model, conf, s))
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["model", "configuration", "n_tasks", "success_rate", "asl_score"])
        for m, c, s in rows:
            w.writerow([m, c, s["n_tasks"], f'{s["success_rate"]:.4f}', f'{s["asl_score"]:.3f}'])
    json.dump([{"model": m, "configuration": c, **s} for m, c, s in extra],
              open(os.path.splitext(a.out)[0] + "_details.json", "w"), indent=1)
    print(open(a.out).read())


if __name__ == "__main__":
    main()
