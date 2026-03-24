#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Convert lean-friendly exercise JSON objects into individual Lean 4 files.

Each exercise is sent to the LLM independently and written as a separate .lean
file (e.g. problem_0001.lean).

Usage (standalone):
    python jsonTolean.py input.json output_dir/ [--prompt PATH] [--model NAME]

When invoked from the pipeline (main.py), the function `convert_json_to_lean`
is the main entry point.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

# ---------------------------------------------------------------------------
# Reuse shared helpers from stdjson.concise_to_lean
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent

sys.path.insert(0, str(_SRC))

from stdjson.concise_to_lean import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    CHAT_FORCE_STREAM,
    _collect_stream_text,
    _is_stream_required_error,
    find_config_json,
    is_exercise_object,
    iter_exercise_objects,
    load_config,
    read_json,
    require_str,
)

DEFAULT_MAX_TOKENS = 8192
DEFAULT_MAX_ATTEMPTS = 5

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_DEFAULT_PROMPT_PATH = _SRC / "prompt" / "json_to_lean.md"

DEFAULT_FALLBACK_PROMPT = """\
You are given a JSON object representing a math problem already in lean-friendly
format. Convert it into a complete Lean 4 + Mathlib file.
Preserve all metadata as a Lean block comment.
Formalize the problem statement; use `by sorry` if a proof is hard.
Output ONLY the Lean file content."""


def load_lean_prompt(prompt_arg: Optional[str] = None) -> str:
    if prompt_arg:
        p = Path(prompt_arg).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Prompt file not found: {p}")
        text = p.read_text(encoding="utf-8").strip()
        if text:
            return text

    if _DEFAULT_PROMPT_PATH.exists():
        text = _DEFAULT_PROMPT_PATH.read_text(encoding="utf-8").strip()
        if text:
            return text

    print("[warn] Using built-in fallback prompt for jsonTolean.", file=sys.stderr)
    return DEFAULT_FALLBACK_PROMPT


# ---------------------------------------------------------------------------
# LLM chat (plain text output, no JSON response_format)
# ---------------------------------------------------------------------------

def chat_completion_lean(
    client: OpenAI,
    *,
    model: str,
    prompt: str,
    max_tokens: int,
) -> str:
    """Call the chat API expecting plain-text (Lean code) output."""
    global CHAT_FORCE_STREAM

    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        top_p=1.0,
        max_tokens=max_tokens,
    )

    if CHAT_FORCE_STREAM is True:
        stream_obj = client.chat.completions.create(stream=True, **kwargs)
        return _collect_stream_text(stream_obj).strip()

    try:
        response = client.chat.completions.create(**kwargs)
        return (response.choices[0].message.content or "").strip()
    except Exception as err:
        if _is_stream_required_error(err):
            CHAT_FORCE_STREAM = True
            stream_obj = client.chat.completions.create(stream=True, **kwargs)
            return _collect_stream_text(stream_obj).strip()
        raise


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------

def extract_lean_code(text: str) -> str:
    """Extract Lean code from the model response.

    Handles:
    1. Raw Lean code (no fences)
    2. Single ```lean ... ``` fenced block
    3. Multiple fenced blocks → join them
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("Model returned empty output.")

    # Try to extract fenced lean blocks
    pattern = r"```(?:lean)?\s*\n(.*?)```"
    blocks = re.findall(pattern, stripped, re.DOTALL)
    if blocks:
        return "\n\n".join(b.strip() for b in blocks if b.strip())

    # No fences — return as-is (likely raw lean code)
    return stripped


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def make_lean_filename(exercise: Dict[str, Any], fallback_index: int) -> str:
    """Generate filename like problem_0001.lean from exercise metadata."""
    idx = exercise.get("index")
    if idx is not None:
        return f"problem_{int(idx):04d}.lean"
    source_idx = exercise.get("source_idx")
    if source_idx:
        safe = re.sub(r"[^\w\-.]", "_", str(source_idx))
        return f"problem_{safe}.lean"
    return f"problem_{fallback_index:04d}.lean"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

METADATA_KEYS = [
    "index", "source_idx", "source", "题目类型", "预估难度",
    "problem", "proof", "direct_answer",
]


def build_prompt(base_prompt: str, exercise: Dict[str, Any]) -> str:
    obj_json = json.dumps(exercise, ensure_ascii=False, indent=2)
    return f"{base_prompt}\n\nInput JSON object:\n{obj_json}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_lean_output(text: str) -> str:
    """Return an error string if the output looks invalid, else empty string."""
    if not text.strip():
        return "Output is empty."
    if text.strip().startswith("{") or text.strip().startswith("["):
        return "Output looks like JSON, not Lean code."
    # Must contain at least one Lean-ish keyword
    lean_markers = ["import", "theorem", "def", "lemma", "variable",
                    "section", "namespace", "sorry", "noncomputable", "open"]
    if not any(m in text for m in lean_markers):
        return "Output does not contain any recognizable Lean keywords."
    return ""


# ---------------------------------------------------------------------------
# Core: convert one exercise to a Lean file
# ---------------------------------------------------------------------------

def convert_one_exercise(
    client: OpenAI,
    *,
    model: str,
    base_prompt: str,
    exercise: Dict[str, Any],
    max_tokens: int,
    max_attempts: int,
) -> str:
    """Send one exercise to the LLM and return Lean code string."""
    last_error = ""

    for attempt in range(1, max_attempts + 1):
        prompt = build_prompt(base_prompt, exercise)
        if last_error and attempt > 1:
            prompt += (
                f"\n\n[Retry] The previous output was invalid: {last_error}\n"
                "Please output ONLY valid Lean 4 code. No JSON, no explanations."
            )

        response_text = chat_completion_lean(
            client, model=model, prompt=prompt, max_tokens=max_tokens,
        )
        try:
            lean_code = extract_lean_code(response_text)
        except Exception as err:
            last_error = str(err)
            continue

        validation_error = validate_lean_output(lean_code)
        if validation_error:
            last_error = validation_error
            continue

        return lean_code

    raise RuntimeError(
        f"Failed to obtain valid Lean code after {max_attempts} attempts: {last_error}"
    )


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------

def convert_json_to_lean(
    input_path: Path,
    output_dir: Path,
    *,
    client: OpenAI,
    model: str,
    base_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    overwrite: bool = False,
) -> List[Path]:
    """Convert all exercises in a JSON file to individual .lean files.

    Returns list of written file paths.
    """
    data = read_json(input_path)
    exercises = list(iter_exercise_objects(data))

    if not exercises:
        print(f"[warn] no exercise objects in {input_path.name}, skipping.", file=sys.stderr)
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(exercises)
    written: List[Path] = []
    failed: List[str] = []

    for idx, exercise in enumerate(exercises, start=1):
        label = exercise.get("source_idx") or exercise.get("index") or str(idx)
        filename = make_lean_filename(exercise, idx)
        out_path = output_dir / filename

        if not overwrite and out_path.exists():
            print(f"  [skip] {filename} (exists)", file=sys.stderr)
            written.append(out_path)
            continue

        print(f"  [{idx}/{total}] converting '{label}' → {filename}", file=sys.stderr)
        try:
            lean_code = convert_one_exercise(
                client,
                model=model,
                base_prompt=base_prompt,
                exercise=exercise,
                max_tokens=max_tokens,
                max_attempts=max_attempts,
            )
            out_path.write_text(lean_code + "\n", encoding="utf-8")
            written.append(out_path)
        except Exception as err:
            failed.append(str(label))
            print(f"  [error] conversion failed for '{label}': {err}", file=sys.stderr)

    print(f"[done] {len(written)}/{total} Lean file(s) written to {output_dir}", file=sys.stderr)
    if failed:
        print(f"  [warn] {len(failed)} failed: {', '.join(failed)}", file=sys.stderr)

    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert lean-friendly exercise JSON into individual Lean 4 files.",
    )
    parser.add_argument("input_json", help="Path to the input JSON file (lean-friendly format).")
    parser.add_argument("output_dir", help="Directory to write .lean files into.")
    parser.add_argument(
        "--prompt", default=None,
        help="Path to the prompt markdown file. Defaults to src/prompt/json_to_lean.md.",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override model name from config.json.",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
        help=f"Maximum completion tokens per exercise (default: {DEFAULT_MAX_TOKENS}).",
    )
    parser.add_argument(
        "--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS,
        help=f"Maximum retry attempts per exercise (default: {DEFAULT_MAX_ATTEMPTS}).",
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Client timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing .lean files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    prompt_text = load_lean_prompt(args.prompt)

    api_key = require_str(config, "api_key")
    base_url = require_str(config, "base_url")
    model = args.model or require_str(config, "model")

    input_path = Path(args.input_json).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=args.timeout)

    convert_json_to_lean(
        input_path,
        output_dir,
        client=client,
        model=model,
        base_prompt=prompt_text,
        max_tokens=args.max_tokens,
        max_attempts=args.max_attempts,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
