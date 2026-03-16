# Conversion Layer Implementation for src/paper/mdTotex.py

## Overview
Added the LLM-based markdown→LaTeX conversion layer to `src/paper/mdTotex.py`. This layer handles the bulk translation from semantic blocks (Markdown) to publication-quality LaTeX, with comprehensive error handling and LaTeX healing.

## Changes Summary

### 1. Core Conversion Functions
- **`markdown_to_latex()`** (line 1300): Main conversion function with:
  - Display-math placeholder preservation to keep `\tag{...}` intact
  - LLM integration with `_chat_complete_text()`
  - Validation against prompt leaks and pathological repetition
  - Fallback to segment-by-segment conversion if placeholders corrupted
  - Full LaTeX healing pipeline

- **`convert_block_to_latex()`** (line 1354): Per-block wrapper that:
  - Passes heading blocks through unchanged
  - Routes statement/proof/paragraph blocks to `markdown_to_latex()`
  - Handles error cases gracefully

- **`convert_blocks_to_latex()`** (line 1383): Orchestration function that:
  - Converts all semantic blocks to LaTeX sequentially (order preservation)
  - Uses tqdm progress bar for visibility
  - Gracefully handles per-block failures with fallback to raw markdown
  - Joins blocks with blank lines for readability

### 2. LaTeX Healing & Sanitization Functions
- **`heal_latex_fragment()`** (line 1230): Core healing pipeline combining:
  - Code fence removal
  - Document wrapper removal (\documentclass...\end{document})
  - Unicode normalization (§ → \S)
  - Math LaTeX sanitization

- **`sanitize_latex_math()`** (line 1217): Math-specific fixes:
  - Operator normalization (\minimize → \min)
  - Display math normalization ($$ → \[...\])
  - Double-backslash correction (\\begin → \begin)
  - Math environment pairing (prevent nested equation envs)

- **`_balance_math_env_pairs()`** (line 1117): Conservative healing of:
  - Illegal nesting (align inside equation)
  - Duplicate \begin{equation}
  - Missing \end{...}
  - Unmatched \end{...}

### 3. Validation Functions
- **`_has_prompt_leak()`** (line 1249): Detects leaked instruction text like:
  - "output only latex"
  - "convert ocr markdown"
  - "<<<proof>>>"
  
- **`_has_pathological_repetition()`** (line 1259): Detects failure modes:
  - >40% of lines are identical
  - Often indicates LLM hang/loop

- **`_validate_llm_tex_output()`** (line 1278): Combined validation with exception:
  - Raises `LowQualityLLMOutput` if validation fails
  - Triggers retry (up to 3 attempts with exponential backoff)

### 4. Utility String Functions
- **`strip_code_fences()`**: Removes markdown code fence wrappers
- **`strip_outer_document()`**: Removes \documentclass...\end{document}
- **`normalize_unicode_symbols()`**: Converts § → \S, etc.
- **`normalize_display_math()`**: Normalizes $$ → \[...\]
- **`normalize_double_backslash_begin_end()`**: Fixes \\begin → \begin

### 5. Integration in main()
Updated main() to orchestrate full pipeline:
```
[preprocess] → [structural] → [conversion] → [assembly] → [output]
```

Specifically:
- Step (10): Call `convert_blocks_to_latex()` with all parameters
- Step (11): Validate output is non-empty
- Step (12): Write LaTeX to output file

## Key Design Decisions

### 1. Display-Math Placeholder Preservation
- Critical for papers with equation numbers
- Prevents LLM from moving/destroying `\tag{...}` markers
- Fallback to segment-by-segment conversion if LLM corrupts placeholders

### 2. Sequential Block Conversion
- Maintains order (important for proofs, examples)
- Prevents erroneous heading/statement merging
- Conservative but correct approach

### 3. Simplified vs. Book Version
- **Papers have cleaner OCR** than textbooks
- Omitted complex healing for:
  - Figure caption wrapping (papers use proper figure environments)
  - Example block balancing (less common in papers)
  - Proof splitting (handled by greedy chunking)
  - Array/bracket rewriting (rare in papers)
- Retained essential healings:
  - Math environment pairing
  - Unicode normalization
  - Operator standardization

### 4. Error Handling
- Per-block error fallback (outputs raw markdown if LLM fails for that block)
- Retry with exponential backoff (up to 3 attempts)
- Validation catches common LLM failure modes

## Testing Status

✓ Syntax validation: `python3 -m py_compile`
✓ Import test: All functions import successfully
✓ Unit tests:
  - `heal_latex_fragment()` - ✓
  - `strip_code_fences()` - ✓
  - `normalize_display_math()` - ✓
  - `_has_prompt_leak()` - ✓
  - All validation functions - ✓

## Next Steps

1. **Post-processing layer** (optional future work):
   - Star all equation environments without tags
   - Attach inline equation numbers
   - Wrap figure/table captions
   
2. **Main orchestration** (optional future work):
   - Build complete LaTeX document from blocks
   - Add preamble with necessary packages
   - Number figures/tables/sections

3. **Testing on papers**:
   - Run on Crouzeix-conjecture and similar papers
   - Validate theorem/proof/algorithm environments
   - Check equation tag preservation

## Code Stats
- **Lines added**: 348
- **New functions**: 23 (core + helpers + validation)
- **New exception class**: 1 (`LowQualityLLMOutput`)
- **Total file size**: 1569 lines (up from 1224)

## Commit Info
- **Hash**: b928087
- **Message**: "feat(paper/mdTotex): add conversion layer (LLM markdown→LaTeX with healing)"
- **Files changed**: 1 (src/paper/mdTotex.py)
- **Insertions**: 348
- **Deletions**: 3

