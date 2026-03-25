import json
import os
from pathlib import Path

# 题目类型映射：命令行参数 -> 中文题目类型
TYPE_MAPPING = {
    "proof_statement": "证明题",
    "calculation":     "计算题",
    "fill_blank":      "填空题",
    "multiple_choice": "选择题",
    "short_answer":    "简答题",
    "application":     "应用题",
}


def load_json_file(filepath: str) -> list[dict]:
    """加载单个 JSON 文件，支持列表或单个对象格式。"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        return []


def extract_by_type(input_dir: str, problem_type: str) -> list[dict]:
    """
    从 input_dir 中所有 JSON 文件里提取 题目类型 == problem_type 的条目。

    :param input_dir:     存放 JSON 文件的目录路径
    :param problem_type:  要筛选的中文题目类型，如 "证明题"
    :return:              匹配的题目列表
    """
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise FileNotFoundError(f"输入目录不存在：{input_dir}")

    results = []
    json_files = sorted(input_path.glob("**/*.json"))

    if not json_files:
        print(f"[警告] 在 {input_dir} 中未找到任何 JSON 文件。")
        return results

    for json_file in json_files:
        try:
            entries = load_json_file(str(json_file))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[跳过] 无法解析文件 {json_file}：{e}")
            continue

        matched = [
            entry for entry in entries
            if isinstance(entry, dict) and entry.get("题目类型") == problem_type
        ]

        if matched:
            print(f'[{json_file.name}] 找到 {len(matched)} 条 "{problem_type}"')
            results.extend(matched)

    return results


def save_results(results: list[dict], output_path: str) -> None:
    """将提取结果保存为 JSON 文件。"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n已将 {len(results)} 条结果保存至：{output_path}")
