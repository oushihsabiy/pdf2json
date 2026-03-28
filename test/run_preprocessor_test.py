#!/usr/bin/env python3
"""Offline test harness for json2lean preprocessor.

This script runs preprocessor.preprocess_all() with a fake API client and
writes results to test/preprocessor_output.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow direct execution without requiring editable install.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from json2lean.models import Exercise
from json2lean.preprocessor import preprocess_all


class FakeAPIClient:
    """Minimal fake client with a chat() interface used by preprocess_all."""

    def __init__(self) -> None:
        self.calls = 0

    def chat(self, *, prompt: str, max_tokens: int = 4096, call_type: str = "", exercise_label: str = "", json_mode: bool = False) -> str:
        self.calls += 1
        # Always return a valid JSON object containing only the rewritten problem field.
        rewritten = (
            "Definition: Let the variables be real numbers.\\n"
            "Hypothesis: Use the statement from the original problem.\\n"
            "Goal: Formalize the statement in Lean without proving it."
        )
        return json.dumps({"problem": rewritten}, ensure_ascii=False)


def build_exercises(items: list[dict]) -> list[Exercise]:
    exercises: list[Exercise] = []
    for i, obj in enumerate(items, 1):
        exercises.append(Exercise(raw=dict(obj), index=i))
    return exercises


def main() -> None:
    input_path = REPO_ROOT / "test" / "preprocessor_input.json"
    output_path = REPO_ROOT / "test" / "preprocessor_output.json"

    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("test/preprocessor_input.json must be a JSON array")

    exercises = build_exercises(data)
    client = FakeAPIClient()
    failed = preprocess_all(client, exercises, max_tokens=512, max_attempts=2)

    result = {
        "failed_labels": failed,
        "api_calls": client.calls,
        "results": [
            {
                "label": ex.label,
                "problem_before": data[idx]["problem"],
                "problem_after": ex.problem,
                "preprocessed_problem": ex.preprocessed_problem,
            }
            for idx, ex in enumerate(exercises)
        ],
    }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {output_path}")
    print(f"Failed labels: {failed}")


if __name__ == "__main__":
    main()
