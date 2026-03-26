"""Parse raw JSON data into Exercise objects."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .models import Exercise


# ------------------------------------------------------------------
# Field-name normalization
# ------------------------------------------------------------------

_FIELD_ALIASES: Dict[str, str] = {
    # problem content
    "题目内容": "problem",
    "问题": "problem",
    "题目": "problem",
    # identifier
    "题目ID": "source_idx",
    "题号": "source_idx",
    "编号": "source_idx",
    # difficulty
    "难度": "预估难度",
    # answer
    "答案": "direct_answer",
    "参考答案": "direct_answer",
    # subject / source
    "科目": "source",
    "来源": "source",
}

# Canonical keys the pipeline expects in a "problem" dict
_PROBLEM_KEY_CANDIDATES = {"problem", "题目内容", "问题", "题目"}
_MARKER_KEYS = {
    "proof", "direct_answer", "source_idx", "source",
    "题目类型", "预估难度",
    # aliases that should also be recognised
    "答案", "难度", "科目", "题目ID", "知识点",
}


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with aliased keys mapped to canonical names.

    Original keys are preserved; canonical aliases are *added* so that
    downstream code always finds the expected key names.
    """
    out = dict(raw)  # shallow copy
    for alias, canonical in _FIELD_ALIASES.items():
        if alias in out and canonical not in out:
            out[canonical] = out[alias]
    # Ensure 'problem' always exists
    if "problem" not in out:
        for k in _PROBLEM_KEY_CANDIDATES:
            if k in out:
                out["problem"] = out[k]
                break
    return out


# ------------------------------------------------------------------
# Exercise detection
# ------------------------------------------------------------------

def is_exercise_object(node: Any) -> bool:
    """Return True if *node* looks like an exercise dict."""
    if not isinstance(node, dict):
        return False
    has_problem = any(k in node for k in _PROBLEM_KEY_CANDIDATES)
    if not has_problem:
        return False
    return any(key in node for key in _MARKER_KEYS)


def _iter_raw(node: Any) -> Iterable[Dict[str, Any]]:
    """Recursively yield exercise dicts from an arbitrarily nested structure."""
    if is_exercise_object(node):
        yield _normalize(node)
        return
    if isinstance(node, list):
        for item in node:
            yield from _iter_raw(item)
        return
    if isinstance(node, dict):
        for item in node.values():
            yield from _iter_raw(item)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def parse_exercises(data: Any) -> List[Exercise]:
    """Extract Exercise objects from loaded JSON data."""
    exercises: List[Exercise] = []
    for idx, raw in enumerate(_iter_raw(data), start=1):
        exercises.append(Exercise(raw=raw, index=idx))
    return exercises
