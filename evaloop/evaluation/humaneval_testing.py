"""HumanEval+ support for the EvaLoop generation <-> summarization loop (Option A extension).

Design problem: MBPP+ prompts end in an ``assert`` line, which the loop re-attaches to every
summary so the function name / call signature survives across cycles (see
``CodeSummarizationTask.postprocess``). HumanEval has no such line: its prompt is a function
header + docstring, with examples in heterogeneous formats (``>>> f(x)``, ``f(x) == y``, prose).

Solution used here: build the *same layout as MBPP+* for HumanEval+,

    \"\"\"
    <docstring text of the entry-point function>
    assert entry_point(<first base test input>) == <canonical output>
    \"\"\"

The anchor assert is generated from the benchmark's own first base test input and the canonical
solution's output, which is exactly what MBPP+ does (its assert is one of the benchmark's tests).
Because the layout is identical, the unmodified summarization postprocess (``splitlines()[-2]``)
keeps the anchor across cycles. No existing task class needs changing.

Testing uses the benchmark's own suites (EvalPlus HumanEval+: ``base`` = original HumanEval tests,
``plus`` = extended tests); a cycle passes only if both pass, as for MBPP+.

The code under test is ``<prelude> + <model code>`` where the prelude is the original prompt's
imports and helper functions (everything except the entry-point function). This mirrors the
standard HumanEval protocol (prompt + completion), so tasks whose prompt ships a helper
(e.g. ``encode_cyclic`` for ``decode_cyclic``) or ``from typing import List`` are not failed for
omitting something the model was never asked to write.
"""

import ast
import functools
import logging
from typing import Any, Dict, Tuple

from evalplus.data import get_human_eval_plus
from evalplus.eval import PASS, untrusted_check
from evalplus.gen.util import trusted_exec

logger = logging.getLogger(__name__)


def _split_prompt(prompt: str, entry_point: str) -> Tuple[str, str]:
    """Returns (docstring of the entry-point function, prelude source of imports/helpers)."""
    tree = ast.parse(prompt)
    docstring, prelude_nodes = "", []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == entry_point:
            docstring = ast.get_docstring(node) or ""
        else:
            prelude_nodes.append(node)
    prelude = "\n".join(ast.unparse(n) for n in prelude_nodes)
    return docstring, prelude


def _anchor_assert(entry_point: str, args, expected) -> str:
    call = ", ".join(repr(a) for a in args)
    return f"assert {entry_point}({call}) == {expected!r}"


@functools.lru_cache(maxsize=1)
def load_humaneval_dataset() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Load HumanEval+ and return (problems, ground_truth), mirroring ``load_mbpp_dataset``.

    ``problems[task_id]["prompt"]`` is the *loop* prompt (docstring + anchor assert). The original
    HumanEval prompt is kept in ``orig_prompt`` and the import/helper prelude in ``prelude``.
    """
    raw = get_human_eval_plus()
    problems, ground_truth = {}, {}
    for task_id, p in raw.items():
        entry = p["entry_point"]
        oracle = {}
        oracle["base"], oracle["base_time"] = trusted_exec(
            p["prompt"] + p["canonical_solution"], p["base_input"], entry, record_time=True
        )
        oracle["plus"], oracle["plus_time"] = trusted_exec(
            p["prompt"] + p["canonical_solution"], p["plus_input"], entry, record_time=True
        )
        ground_truth[task_id] = oracle

        docstring, prelude = _split_prompt(p["prompt"], entry)
        anchor = _anchor_assert(entry, p["base_input"][0], oracle["base"][0])
        loop_prompt = f'"""\n{docstring}\n{anchor}\n"""\n'

        q = dict(p)
        q["orig_prompt"] = p["prompt"]
        q["prelude"] = prelude
        q["prompt"] = loop_prompt
        problems[task_id] = q
    logger.info("Loaded %d HumanEval+ problems", len(problems))
    return problems, ground_truth


class HumanEvalPlusCodeTester:
    """Tests generated code against the HumanEval+ base and plus suites (EvalPlus)."""

    def __init__(self, problems, ground_truth):
        self.problems = problems
        self.ground_truth = ground_truth
        self.logger = logging.getLogger(__name__)

    def test_code(self, code: str, task_id: str, entry_point: str) -> Dict[str, Any]:
        try:
            problem = self.problems.get(task_id)
            expected = self.ground_truth.get(task_id)
            if not problem or not expected:
                return {"success": False, "error": f"Task {task_id} not found", "plus_details": []}

            full_code = (problem["prelude"] + "\n\n" + code) if problem["prelude"] else code
            results = {}
            for split in ("base", "plus"):
                results[split] = untrusted_check(
                    "humaneval",
                    full_code,
                    problem[f"{split}_input"],
                    entry_point,
                    expected=expected[split],
                    atol=problem.get("atol", 0),
                    ref_time=expected[f"{split}_time"],
                    fast_check=False,
                    min_time_limit=1.0,
                    gt_time_limit_factor=2.0,
                )
            base_ok = results["base"][0] == PASS
            plus_ok = results["plus"][0] == PASS
            return {
                "success": base_ok and plus_ok,
                "base_success": base_ok,
                "plus_success": plus_ok,
                "base_details": results["base"][1],
                "plus_details": results["plus"][1],
            }
        except Exception as e:  # untrusted code must never crash the run
            self.logger.error("Error testing code: %s", e)
            return {"success": False, "error": str(e), "plus_details": []}
