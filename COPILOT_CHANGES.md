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

## 2026-03-26

### 变更任务
- 修复 token 统计日志长期显示 0 的问题，补齐流式与缺失 usage 场景的计数策略。

### 具体修改内容
- 更新 [src/json2lean/models.py](src/json2lean/models.py)：
	- 在 `TokenUsage` 中新增 `usage_source` 字段，用于标识 token 来源（`api` / `api_stream` / `estimated` / `none`）。
	- `to_dict()` 输出新增 `usage_source`，便于排查第三方网关是否返回 usage。
- 更新 [src/json2lean/api_client.py](src/json2lean/api_client.py)：
	- 流式读取 `_collect_stream()` 现在会尝试解析流事件里的 `usage`。
	- `_do_stream()` 启用 `stream_options={"include_usage": True}`，优先获取服务端真实统计。
	- 在非流式和流式两条路径上分别写入 usage，并标注 `usage_source`。
	- 增加 `_estimate_tokens()` 估算兜底：当服务端不返回 usage 时，用近似规则估算 prompt/completion/total，避免日志全 0。

### 验证与现状
- 本地静态检查通过：修改文件无类型/语法错误。
- 运行验证命令时多次被 `KeyboardInterrupt` 中断，导致新 token 日志未完整落盘；因此尚未生成包含新字段的最新日志样本。

### 影响范围
- [src/json2lean/api_client.py](src/json2lean/api_client.py) 的 token 记录逻辑。
- [src/json2lean/models.py](src/json2lean/models.py) 的 token 日志结构。
