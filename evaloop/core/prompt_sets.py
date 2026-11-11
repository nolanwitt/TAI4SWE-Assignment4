"""Named prompt sets for the generation <-> summarization loop.

``default``  : templates hard-coded in ``EvaluationConfig.get_task_configs`` (one-sentence summary
               that starts with "write a python function to").
``assignment``: the exact templates the course data package says produced the MBPP+ baseline
               records (``prompts/task_prompts.md``). Use this for runs that must be comparable
               with that baseline. NOTE: it differs from ``default`` - baseline and extension must
               use the same set.
"""

PROMPT_SETS = {
    "assignment": {
        "generation": (
            "Generate Python code for the following task:\n\n{description}\n\n"
            "Return only the code, without explanations or comments."
        ),
        "summarization": (
            "Summarize what the following code does in a detailed description:\n\n"
            "```\n{code}\n```\n\n"
            "Return only the summary, without explanations or comments."
        ),
    }
}
