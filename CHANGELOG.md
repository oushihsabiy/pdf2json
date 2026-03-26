# Changelog

## 2025-03-26 — 项目构建 & 端到端修复

### 新增
- **完整项目架构**：按 `src/json2lean/` 包结构重构，共 14 个模块
  - `parser.py` — JSON 解析（支持中英文字段名自动映射）
  - `preprocessor.py` — LLM 预处理（将题目改写为 Definition/Hypothesis/Goal 格式）
  - `translater.py` — LLM 翻译（Lean 4 代码生成）
  - `validator.py` — Lean 编译验证（`lake env lean`）
  - `recover.py` — LLM 自动修复循环（最多 N 次重试）
  - `api_client.py` — OpenAI API 封装（token 跟踪、流式传输自动检测）
  - `models.py` — 数据模型（Exercise, CompileResult, TokenUsage, PipelineConfig）
  - `loader.py` — JSON / 配置 / Prompt 文件加载
  - `writer.py` — .lean 文件写入
  - `comment_builder.py` — Lean 注释头构建
  - `lean_env.py` — Lean 4 环境检测
  - `main.py` — 流水线调度 & CLI 入口
  - `__main__.py` / `__init__.py` — 包入口
- **Prompt 模板**：`prompts/concise_to_lean.md`、`prompts/json_to_lean.md`、`prompts/recovery.md`
- **Lean 4 项目**：`lean/` 目录，依赖 Mathlib v4.28.0，已下载完整 oleans 缓存
- **配置示例**：`config.example.json`
- **构建配置**：`pyproject.toml`（setuptools）、`requirements.txt`
- **文档**：`README.md`（使用指南 + CLI 参数 + 架构说明）
- **示例数据**：`data/sample_math.json`（4 道中文数学题）

### 修复
- **parser.py**：新增 `_FIELD_ALIASES` 字典，自动将中文字段名（题目内容 → problem、题目ID → source_idx 等）映射为英文规范名
- **models.py**：`Exercise.__post_init__` 增加 `题目ID` / `题目内容` 回退逻辑
- **preprocessor.py**：放宽 `_validate_candidate` 校验（仅检查 `problem` 字段存在），避免因 JSON schema 差异导致预处理失败
- **validator.py**：修复只解析 stdout 的问题，现在同时解析 `stderr`，确保正确捕获编译错误
- **pyproject.toml**：修复 `build-backend` 为 `setuptools.build_meta`（原值 `setuptools.backends._legacy:_Backend` 不可用）

### 验证结果
使用 `python3 -m json2lean data/sample_math.json -o outputs` 运行全流水线：

| 文件 | 题型 | 编译状态 |
|------|------|----------|
| C001.lean | 计算题（∫₀¹ x²dx = 1/3） | ✅ 通过（完整证明） |
| P001.lean | 证明题（立方和公式） | ✅ 通过（sorry 占位） |
| P002.lean | 证明题（介值定理） | ✅ 通过（sorry 占位） |
| F001.lean | 填空题（sinx/x → 1） | ✅ 通过（sorry 占位） |

### .gitignore 更新
- 新增排除：`lean/.lake/`、`lean/lake-packages/`、`lean/build/`（Mathlib 缓存 ~6.8GB）
