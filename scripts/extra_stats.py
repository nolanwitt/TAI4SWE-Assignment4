"""Extra descriptive statistics for an EvaLoop results file (used in the report).
Usage: python scripts/extra_stats.py RESULTS.json
"""
import json, re, sys, statistics as st
d = json.load(open(sys.argv[1], encoding="utf8")); d = d[0] if isinstance(d, list) else d
P = d["prompt_results"]; T = len(P)
sc = [r["successful_cycles"] for r in P]
print("n_tasks", T, "histogram", [sc.count(i) for i in range(11)])
print("cumulative pass@k %:", [round(100 * sum(s >= k for s in sc) / T, 1) for k in range(1, 11)])
f1 = [r for r in P if r["successful_cycles"] == 0]
late = [r for r in P if 0 < r["successful_cycles"] < 10]
print("fail@1", len(f1), "fail later", len(late), "survived10", sum(s == 10 for s in sc))
def split(rs):
    c = {"base_ok_plus_fail": 0, "base_fail": 0}
    for r in rs:
        t = r["cycles"][-1].get("test_results", {})
        c["base_ok_plus_fail" if t.get("base_success") else "base_fail"] += 1
    return c
print("fail@1 split", split(f1), "| later split", split(late))
# fraction of generated code echoing the anchor assert (top-level assert statement in code)
ech = tot = 0
for r in P:
    for c in r["cycles"]:
        code = c.get("task_1_output", "")
        tot += 1
        ech += bool(re.search(r"^assert ", code, re.M))
print("code containing top-level assert: %d/%d (%.1f%%)" % (ech, tot, 100 * ech / tot))
L = [len(c["task_2_output"]) for r in P for c in r["cycles"] if "task_2_output" in c]
print("summary chars median", st.median(L), "mean", round(st.mean(L)))
