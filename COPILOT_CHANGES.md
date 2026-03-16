# Copilot Change Log

用于记录每次由 Copilot 进行的代码修改细节。后续每次修改代码后，都会先更新本文件，再执行 git add/commit/push。

## 2026-03-16

### 变更任务
- 新增持续变更记录机制：以后每次代码修改都整理到本文件并上传到 GitHub。

### 具体修改内容
- 新建文件 `COPILOT_CHANGES.md` 作为统一变更记录。
- 约定记录格式：日期 -> 变更任务 -> 具体修改内容。
- 约定提交流程：每次代码修改后，先更新本文件，再提交并推送。

### 影响范围
- 仅新增文档，不影响现有代码执行逻辑。

### 变更任务
- 调整 paper 的 Markdown 转 LaTeX 逻辑，禁止在 theorem/lemma/proposition/corollary/definition 环境内部内嵌 proof。

### 具体修改内容
- 更新 [src/paper/mdTotex.py](src/paper/mdTotex.py) 的提示词，明确要求 proof 必须作为独立的外置 `\\begin{proof} ... \\end{proof}` 块输出。
- 新增后处理逻辑：如果模型仍把 `proof` 生成在 `thm/lem/prop/cor/defn` 环境内部，会自动拆出并移动到对应 theorem-like 环境之后。
- 将 proof 外提逻辑放在 LaTeX 清洗阶段统一执行，减少下游解析歧义。

### 影响范围
- [src/paper/mdTotex.py](src/paper/mdTotex.py) 生成的 LaTeX 结构更稳定，便于 [src/paper/texTojson.py](src/paper/texTojson.py) 后续解析 theorem 与 proof 的对应关系。
