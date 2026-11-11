"""OpenAI-compatible local/hosted endpoint (Ollama, vLLM, ...) with threaded batch generation.

Reuses ``OpenAILLM`` (retry logic, greedy defaults). Defining ``batch_generate`` makes
``BatchEvaluationCycle`` run every cycle in batch mode, so a local server can serve many tasks
concurrently without any change to the cycle runner.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from .closed_source import OpenAILLM


class OpenAICompatibleLLM(OpenAILLM):
    def __init__(self, model_config: Dict[str, Any]):
        model_config = dict(model_config)
        model_config.setdefault("api_key", "not-needed")  # local servers ignore the key
        super().__init__(model_config)
        self.max_workers = int(model_config.get("max_workers", 8))
        self.seed = model_config.get("seed")
        self.max_retries = 3

    def __str__(self) -> str:
        return f"OpenAICompatibleLLM({self.model_id} @ {self.base_url})"

    def generate(self, prompt: str, **kwargs) -> str:
        if self.seed is not None:
            kwargs.setdefault("seed", self.seed)
        out = super().generate(prompt, **kwargs)
        if out.startswith("Error generating response"):
            # Never feed an API error string to the loop as if it were model output.
            raise RuntimeError(out)
        return out

    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        # Per-prompt failures become empty strings -> an extraction/test failure for that task only.
        def one(p: str) -> str:
            try:
                return self.generate(p, **kwargs)
            except Exception:
                return ""

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(one, prompts))
