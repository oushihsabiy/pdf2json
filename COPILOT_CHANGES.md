# Copilot Change Log

## 2026-03-16

### 变更任务
- 在 src/paper 中创建新的 mdTotex.py，用于将 pdfTomd.py 产出的 Markdown 转为可编译 LaTeX。

### 具体修改内容
- 新建 [src/paper/mdTotex.py](src/paper/mdTotex.py)，实现命令行接口：python mdTotex.py input.md output.tex。
- 按模块实现函数：read_markdown、parse_blocks、convert_headings、convert_equations、convert_lists、convert_images、convert_tables、convert_math_environments、generate_latex_document、write_tex。
- 增加完整文档模板：article + amsmath/amssymb/amsthm/graphicx/hyperref/booktabs，并定义 theorem/lemma/proposition/corollary/definition 环境。
- 支持核心 Markdown 结构转换：标题、粗体/斜体、行内公式、块公式、列表、引用、图片、代码块、表格（booktabs 风格）。
- 增加数学结构识别：Theorem、Lemma、Proposition、Definition、Corollary、Proof。
- 对 theorem 类段落中的内嵌 Proof. 做外置化处理，输出独立 \begin{proof} ... \end{proof}。
- 增加健壮性处理：输入输出后缀校验、异常捕获、无法识别结构最小改写保留。

### 影响范围
- 新增文件 [src/paper/mdTotex.py](src/paper/mdTotex.py)。
- 更新记录文件 [COPILOT_CHANGES.md](COPILOT_CHANGES.md)。
