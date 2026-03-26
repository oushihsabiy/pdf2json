"""OpenAI API client wrapper with token-usage tracking."""

from __future__ import annotations

import json
import math
import sys
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .models import TokenUsage


class APIClient:
    """Thin wrapper around OpenAI that records token consumption."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 180.0,
    ) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self.model = model
        self._force_stream: Optional[bool] = None
        self.usage_log: List[TokenUsage] = []

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_stream(stream: Any) -> tuple[str, Optional[Dict[str, int]]]:
        parts: List[str] = []
        usage: Optional[Dict[str, int]] = None
        try:
            for chunk in stream:
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage:
                    usage = {
                        "prompt_tokens": getattr(chunk_usage, "prompt_tokens", 0) or 0,
                        "completion_tokens": getattr(chunk_usage, "completion_tokens", 0) or 0,
                        "total_tokens": getattr(chunk_usage, "total_tokens", 0) or 0,
                    }
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                if delta is None:
                    continue
                content = getattr(delta, "content", None)
                if isinstance(content, str):
                    parts.append(content)
        finally:
            close_fn = getattr(stream, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
        return "".join(parts), usage

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate fallback when provider omits usage."""
        stripped = (text or "").strip()
        if not stripped:
            return 0
        return max(1, math.ceil(len(stripped) / 4))

    # ------------------------------------------------------------------
    # Core chat call
    # ------------------------------------------------------------------

    def chat(
        self,
        *,
        prompt: str,
        max_tokens: int = 4096,
        call_type: str = "",
        exercise_label: str = "",
        json_mode: bool = False,
    ) -> str:
        """Send a chat-completion request and return the assistant text.

        Token usage (if reported by the API) is appended to
        ``self.usage_log``.
        """
        kwargs: Dict[str, Any] = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        usage = TokenUsage(call_type=call_type, exercise_label=exercise_label)

        # Try non-streaming first; fall back to streaming if forced.
        if self._force_stream is True:
            text, stream_usage = self._do_stream(kwargs)
            if stream_usage:
                usage.prompt_tokens = stream_usage["prompt_tokens"]
                usage.completion_tokens = stream_usage["completion_tokens"]
                usage.total_tokens = stream_usage["total_tokens"]
                usage.usage_source = "api_stream"
        else:
            try:
                resp = self._client.chat.completions.create(**kwargs)
                text = (resp.choices[0].message.content or "").strip()
                # Record token usage from response
                if hasattr(resp, "usage") and resp.usage:
                    usage.prompt_tokens = resp.usage.prompt_tokens or 0
                    usage.completion_tokens = resp.usage.completion_tokens or 0
                    usage.total_tokens = resp.usage.total_tokens or 0
                    usage.usage_source = "api"
            except Exception as err:
                if "stream must be set to true" in str(err).lower():
                    self._force_stream = True
                    text, stream_usage = self._do_stream(kwargs)
                    if stream_usage:
                        usage.prompt_tokens = stream_usage["prompt_tokens"]
                        usage.completion_tokens = stream_usage["completion_tokens"]
                        usage.total_tokens = stream_usage["total_tokens"]
                        usage.usage_source = "api_stream"
                else:
                    raise

        if usage.total_tokens <= 0:
            usage.prompt_tokens = self._estimate_tokens(prompt)
            usage.completion_tokens = self._estimate_tokens(text)
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            usage.usage_source = "estimated"

        self.usage_log.append(usage)
        return text

    def _do_stream(self, kwargs: Dict[str, Any]) -> tuple[str, Optional[Dict[str, int]]]:
        stream = self._client.chat.completions.create(
            stream=True,
            stream_options={"include_usage": True},
            **kwargs,
        )
        text, usage = self._collect_stream(stream)
        return text.strip(), usage

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def total_usage(self) -> Dict[str, int]:
        totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for u in self.usage_log:
            totals["prompt_tokens"] += u.prompt_tokens
            totals["completion_tokens"] += u.completion_tokens
            totals["total_tokens"] += u.total_tokens
        return totals

    def dump_usage(self) -> List[Dict[str, Any]]:
        return [u.to_dict() for u in self.usage_log]


# ------------------------------------------------------------------
# JSON extraction utility (shared by preprocessor & translater)
# ------------------------------------------------------------------

def extract_json_value(text: str) -> Any:
    """Best-effort extraction of a JSON value from model output."""
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("Model returned empty output.")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Try inside code fences
    fence_start = stripped.find("```")
    if fence_start >= 0:
        fence_end = stripped.rfind("```")
        if fence_end > fence_start:
            fenced = stripped[fence_start + 3 : fence_end].strip()
            nl = fenced.find("\n")
            if nl >= 0 and fenced[:nl].strip().lower() in ("json", ""):
                fenced = fenced[nl + 1 :].strip()
            try:
                return json.loads(fenced)
            except json.JSONDecodeError:
                pass

    # Try first { … } or [ … ]
    for open_ch, close_ch in [("{", "}"), ("[", "]")]:
        start = stripped.find(open_ch)
        end = stripped.rfind(close_ch)
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass

    raise ValueError("Model output is not valid JSON.")


def extract_lean_code(text: str) -> str:
    """Extract Lean code from a model response (handles code fences)."""
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("Model returned empty output.")

    # If wrapped in ```lean … ```
    fence_start = stripped.find("```")
    if fence_start >= 0:
        fence_end = stripped.rfind("```")
        if fence_end > fence_start:
            inner = stripped[fence_start + 3 : fence_end].strip()
            nl = inner.find("\n")
            if nl >= 0 and inner[:nl].strip().lower() in ("lean", "lean4", ""):
                inner = inner[nl + 1 :]
            return inner.strip()

    return stripped
