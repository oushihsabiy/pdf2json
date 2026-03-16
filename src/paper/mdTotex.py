#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Convert paper-oriented Markdown into compile-ready LaTeX."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"^\s*!\[(.*?)\]\((.*?)\)\s*$")
THEOREM_MARK_RE = re.compile(
    r"^\s*(Theorem|Lemma|Proposition|Definition|Corollary)\s+(\d+(?:\.\d+)*)\s*\.?\s*$",
    re.IGNORECASE,
)
PROOF_MARK_RE = re.compile(r"^\s*Proof\s*\.?\s*$", re.IGNORECASE)
# Inline bold format: **Theorem 1** content...  or  **Theorem 1.2** *content...*
THEOREM_INLINE_RE = re.compile(
    r"^\*\*(Theorem|Lemma|Proposition|Definition|Corollary)"
    r"\s+(\d+(?:\.\d+)*)(?:\s*\([^)]*\))?\*\*\s*(.*)",
    re.IGNORECASE,
)
# Inline italic proof: *Proof* content...  or  *Proof of Theorem N* content...
PROOF_INLINE_RE = re.compile(
    r"^\*(Proof(?:\s+of\s+[^*]*)?)\*\s*(.*)",
    re.IGNORECASE,
)
_THEOREM_ENV_MAP = {
    "theorem": "theorem",
    "lemma": "lemma",
    "proposition": "proposition",
    "definition": "definition",
    "corollary": "corollary",
}
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def read_markdown(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Input Markdown file not found: {path}")
    if path.suffix.lower() != ".md":
        raise ValueError(f"Input file must be a .md file: {path}")
    return path.read_text(encoding="utf-8")


def split_inline_math(text: str) -> List[Tuple[str, bool]]:
    parts: List[Tuple[str, bool]] = []
    pattern = re.compile(r"(\$[^$\n]+\$)")
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            parts.append((text[last:m.start()], False))
        parts.append((m.group(1), True))
        last = m.end()
    if last < len(text):
        parts.append((text[last:], False))
    return parts


def escape_latex_text(text: str) -> str:
    text = re.sub(r"(?<!\\)([%&_#])", r"\\\1", text)
    return text


def convert_links(text: str) -> str:
    return re.sub(r"\[(.+?)\]\((.+?)\)", r"\\href{\2}{\1}", text)


def convert_emphasis(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\\textit{\1}", text)
    return text


def convert_inline_text(text: str) -> str:
    segments = split_inline_math(text)
    out: List[str] = []
    for seg, is_math in segments:
        if is_math:
            out.append(seg)
            continue
        seg = convert_links(seg)
        seg = convert_emphasis(seg)
        seg = escape_latex_text(seg)
        out.append(seg)
    return "".join(out)


def parse_blocks(markdown: str) -> List[Dict[str, str]]:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: List[Dict[str, str]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.strip().startswith("```"):
            code_lines: List[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1
            blocks.append({"type": "code", "content": "\n".join(code_lines)})
            continue

        if line.strip().startswith("$$"):
            start = line.strip()
            if start != "$$" and start.endswith("$$") and len(start) > 4:
                content = start[2:-2].strip()
                blocks.append({"type": "equation", "content": content})
                i += 1
                continue
            eq_lines: List[str] = []
            i += 1
            while i < n and lines[i].strip() != "$$":
                eq_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1
            blocks.append({"type": "equation", "content": "\n".join(eq_lines).strip()})
            continue

        if HEADING_RE.match(line.strip()):
            blocks.append({"type": "heading", "content": line.strip()})
            i += 1
            continue

        if IMAGE_RE.match(line.strip()):
            blocks.append({"type": "image", "content": line.strip()})
            i += 1
            continue

        if i + 1 < n and "|" in line and TABLE_SEP_RE.match(lines[i + 1]):
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            blocks.append({"type": "table", "content": "\n".join(table_lines)})
            continue

        if line.lstrip().startswith(">"):
            quote_lines: List[str] = []
            while i < n and lines[i].lstrip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append({"type": "quote", "content": "\n".join(quote_lines).strip()})
            continue

        if BULLET_RE.match(line):
            items: List[str] = []
            while i < n and BULLET_RE.match(lines[i]):
                m = BULLET_RE.match(lines[i])
                items.append(m.group(1) if m else lines[i].strip())
                i += 1
            blocks.append({"type": "itemize", "content": "\n".join(items)})
            continue

        if NUMBERED_RE.match(line):
            items = []
            while i < n and NUMBERED_RE.match(lines[i]):
                m = NUMBERED_RE.match(lines[i])
                items.append(m.group(1) if m else lines[i].strip())
                i += 1
            blocks.append({"type": "enumerate", "content": "\n".join(items)})
            continue

        para_lines: List[str] = [line]
        i += 1
        while i < n:
            cur = lines[i]
            if not cur.strip():
                break
            if cur.strip().startswith("```") or cur.strip().startswith("$$"):
                break
            if HEADING_RE.match(cur.strip()) or IMAGE_RE.match(cur.strip()):
                break
            if cur.lstrip().startswith(">"):
                break
            if BULLET_RE.match(cur) or NUMBERED_RE.match(cur):
                break
            if i + 1 < n and "|" in cur and TABLE_SEP_RE.match(lines[i + 1]):
                break
            para_lines.append(cur)
            i += 1
        blocks.append({"type": "paragraph", "content": "\n".join(para_lines).strip()})

    return blocks


def convert_headings(heading_line: str) -> str:
    m = HEADING_RE.match(heading_line)
    if not m:
        return convert_inline_text(heading_line)
    level = len(m.group(1))
    title = convert_inline_text(m.group(2).strip())
    if level == 1:
        return f"\\section{{{title}}}"
    if level == 2:
        return f"\\subsection{{{title}}}"
    return f"\\subsubsection{{{title}}}"


def convert_equations(content: str) -> str:
    body = content.strip()
    if "\\\\" in body:
        return "\\begin{align}\n" + body + "\n\\end{align}"
    return "\\begin{equation}\n" + body + "\n\\end{equation}"


def convert_lists(block_type: str, content: str) -> str:
    env = "itemize" if block_type == "itemize" else "enumerate"
    items = [ln for ln in content.split("\n") if ln.strip()]
    body = "\n".join([f"\\item {convert_inline_text(it.strip())}" for it in items])
    return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"


def convert_images(image_line: str) -> str:
    m = IMAGE_RE.match(image_line)
    if not m:
        return convert_inline_text(image_line)
    caption = convert_inline_text(m.group(1).strip())
    path = m.group(2).strip()
    return (
        "\\begin{figure}[h]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.8\\textwidth]{{{path}}}\n"
        f"\\caption{{{caption}}}\n"
        "\\end{figure}"
    )


def split_table_row(row: str) -> List[str]:
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def convert_tables(table_block: str) -> str:
    rows = [ln for ln in table_block.split("\n") if ln.strip()]
    if len(rows) < 2:
        return convert_inline_text(table_block)

    header = split_table_row(rows[0])
    body_rows = [split_table_row(r) for r in rows[2:]]
    col_count = len(header)
    if col_count == 0:
        return convert_inline_text(table_block)

    align = "l" * col_count
    header_line = " & ".join(convert_inline_text(c) for c in header) + r" \\"
    body_lines = []
    for row in body_rows:
        normalized = row + [""] * max(0, col_count - len(row))
        normalized = normalized[:col_count]
        body_lines.append(" & ".join(convert_inline_text(c) for c in normalized) + r" \\")

    table_lines = [
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        header_line,
        "\\midrule",
        *body_lines,
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(table_lines)


def convert_math_environments(paragraph: str) -> str:
    lines = [ln.rstrip() for ln in paragraph.split("\n") if ln.strip()]
    if not lines:
        return ""

    first = lines[0].strip()

    # Pattern 1: standalone theorem marker on its own line, e.g. "Theorem 1"
    tmatch = THEOREM_MARK_RE.match(first)
    if tmatch:
        name = tmatch.group(1).lower()
        env = _THEOREM_ENV_MAP.get(name, "theorem")
        body_lines = lines[1:]

        proof_index = -1
        for idx, ln in enumerate(body_lines):
            if PROOF_MARK_RE.match(ln.strip()):
                proof_index = idx
                break

        if proof_index >= 0:
            theorem_part = body_lines[:proof_index]
            proof_part = body_lines[proof_index + 1:]
            theorem_body = "\n".join(convert_inline_text(ln) for ln in theorem_part).strip()
            proof_body = "\n".join(convert_inline_text(ln) for ln in proof_part).strip()
            theorem_block = f"\\begin{{{env}}}\n{theorem_body}\n\\end{{{env}}}"
            proof_block = f"\\begin{{proof}}\n{proof_body}\n\\end{{proof}}"
            return theorem_block + "\n\n" + proof_block

        body = "\n".join(convert_inline_text(ln) for ln in body_lines).strip()
        return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"

    # Pattern 2: inline bold format: **Theorem 1** content...
    imatch = THEOREM_INLINE_RE.match(first)
    if imatch:
        name = imatch.group(1).lower()
        env = _THEOREM_ENV_MAP.get(name, "theorem")
        first_content = imatch.group(3).strip()
        # Strip surrounding italic markers if the content is wrapped in *...*
        first_content = re.sub(r"^\*(.+)\*$", r"\1", first_content)
        body_lines = ([first_content] if first_content else []) + lines[1:]
        body = "\n".join(convert_inline_text(ln) for ln in body_lines).strip()
        return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"

    # Pattern 3: inline italic proof: *Proof* content...  or  *Proof of Theorem N* content...
    pmatch = PROOF_INLINE_RE.match(first)
    if pmatch:
        first_content = pmatch.group(2).strip()
        body_lines = ([first_content] if first_content else []) + lines[1:]
        body = "\n".join(convert_inline_text(ln) for ln in body_lines).strip()
        return f"\\begin{{proof}}\n{body}\n\\end{{proof}}"

    # Pattern 4: standalone "Proof." on its own line
    if PROOF_MARK_RE.match(first):
        body_lines = lines[1:]
        body = "\n".join(convert_inline_text(ln) for ln in body_lines).strip()
        return f"\\begin{{proof}}\n{body}\n\\end{{proof}}"

    return ""


def convert_quotes(content: str) -> str:
    text = "\n".join(convert_inline_text(ln) for ln in content.split("\n"))
    return "\\begin{quote}\n" + text + "\n\\end{quote}"


def convert_paragraph(content: str) -> str:
    env_block = convert_math_environments(content)
    if env_block:
        return env_block
    text_lines = [convert_inline_text(ln) for ln in content.split("\n")]
    return "\n".join(text_lines)


def generate_latex_document(content: str) -> str:
    preamble = (
        "\\documentclass{article}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usepackage{amsthm}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{booktabs}\n\n"
        "\\newtheorem{theorem}{Theorem}\n"
        "\\newtheorem{lemma}{Lemma}\n"
        "\\newtheorem{proposition}{Proposition}\n"
        "\\newtheorem{corollary}{Corollary}\n"
        "\\theoremstyle{definition}\n"
        "\\newtheorem{definition}{Definition}\n\n"
        "\\begin{document}\n\n"
    )
    ending = "\n\\end{document}\n"
    return preamble + content.strip() + ending


def write_tex(path: Path, latex_content: str) -> None:
    name = path.name.lower()
    if not (name.endswith(".tex") or name.endswith(".tex.tmp")):
        raise ValueError(f"Output file must be a .tex or .tex.tmp file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(latex_content, encoding="utf-8")


def convert_markdown_to_latex(md_text: str) -> str:
    blocks = parse_blocks(md_text)
    latex_blocks: List[str] = []

    for block in blocks:
        btype = block.get("type", "")
        content = block.get("content", "")

        if btype == "heading":
            latex_blocks.append(convert_headings(content))
        elif btype == "equation":
            latex_blocks.append(convert_equations(content))
        elif btype in {"itemize", "enumerate"}:
            latex_blocks.append(convert_lists(btype, content))
        elif btype == "image":
            latex_blocks.append(convert_images(content))
        elif btype == "table":
            latex_blocks.append(convert_tables(content))
        elif btype == "quote":
            latex_blocks.append(convert_quotes(content))
        elif btype == "code":
            latex_blocks.append("\\begin{verbatim}\n" + content + "\n\\end{verbatim}")
        elif btype == "paragraph":
            latex_blocks.append(convert_paragraph(content))
        else:
            # Keep unknown structures with minimal transformation.
            latex_blocks.append(convert_inline_text(content))

    joined = "\n\n".join([b for b in latex_blocks if b.strip()])
    return generate_latex_document(joined)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Markdown from pdfTomd.py to compile-ready LaTeX for math/optimization papers."
    )
    parser.add_argument("input_md", help="Path to input Markdown file")
    parser.add_argument("output_tex", help="Path to output TeX file")
    parser.add_argument("--workers", type=int, default=None, help="(ignored) Worker count placeholder for pipeline compatibility")
    return parser


def main() -> None:
    parser = build_cli_parser()
    args = parser.parse_args()

    in_path = Path(args.input_md).expanduser().resolve()
    out_path = Path(args.output_tex).expanduser().resolve()

    try:
        md_text = read_markdown(in_path)
        latex_text = convert_markdown_to_latex(md_text)
        write_tex(out_path, latex_text)
        print(f"DONE: {out_path}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
