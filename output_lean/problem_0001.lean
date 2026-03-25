/-
index: 1
source_idx: test_001
source: test
题目类型: 凸优化
预估难度: easy
problem:
\[\begin{aligned}
&\text{Definition: } f : \mathbf{R}^n \to \mathbf{R}.\\
&\text{Definition: } S = \{x \mid f(x) \le 0\}.\\
&\text{Hypothesis: } f \text{ is convex.}\\
&\text{Goal: prove that } S \text{ is convex.}
\end{aligned}\]
proof:

direct_answer:

-/

import Mathlib

noncomputable section

open Set

variable {n : ℕ}

/-- The sublevel set `{x | f x ≤ 0}` of a convex function `f : ℝⁿ → ℝ` is convex. -/
theorem convex_sublevel_set_of_convex
    (f : (Fin n → ℝ) → ℝ)
    (hconv : ConvexOn ℝ (Set.univ : Set (Fin n → ℝ)) f) :
    Convex ℝ {x : Fin n → ℝ | f x ≤ 0} := by
  sorry
