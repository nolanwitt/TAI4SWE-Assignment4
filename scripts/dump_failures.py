"""Dump failed loops from an EvaLoop results file into a readable text file for manual inspection.

Usage: python scripts/dump_failures.py RESULTS.json OUT.txt [--max N] [--min-cycle K]
For each failed task: initial prompt, the last passing summary (the prompt that led to the failing
cycle), the failing code, and the test outcome.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results"); ap.add_argument("out")
    ap.add_argument("--max", type=int, default=1000)
    ap.add_argument("--min-cycle", type=int, default=1, help="only failures at cycle >= K")
    a = ap.parse_args()
    d = json.load(open(a.results, encoding="utf8"))
    d = d[0] if isinstance(d, list) else d
    n = 0
    with open(a.out, "w", encoding="utf8") as f:
        for r in d["prompt_results"]:
            if r["max_cycles_reached"]:
                continue
            fail = r["cycles"][-1]
            if fail["cycle"] < a.min_cycle:
                continue
            n += 1
            if n > a.max:
                break
            tr = fail.get("test_results", {})
            prev = r["cycles"][-2].get("task_2_output", "") if len(r["cycles"]) > 1 else ""
            f.write(f"{'=' * 80}\n{r['task_id']}  failed at cycle {fail['cycle']}  "
                    f"base={tr.get('base_success')} plus={tr.get('plus_success')} err={tr.get('error')}\n")
            f.write(f"--- INITIAL PROMPT\n{r['initial_prompt']}\n")
            f.write(f"--- PROMPT FOR FAILING CYCLE (previous summary)\n{prev}\n" if prev else "")
            f.write(f"--- FAILING CODE\n{fail.get('task_1_output', '')}\n")
            f.write(f"--- RAW OUTPUT (head)\n{str(fail.get('task_1_raw_output', ''))[:400]}\n")
            f.write(f"--- TEST DETAILS\n{str(tr.get('base_details'))[:200]} | {str(tr.get('plus_details'))[:200]}\n")
    print(f"wrote {min(n, a.max)} failed loops to {a.out}")


if __name__ == "__main__":
    main()
