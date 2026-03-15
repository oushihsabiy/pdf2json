import re
import json
import os
import requests
from openai import OpenAI

def extract_math_environments(latex_content):
    """
    Extract definition, lemma, proposition, theorem, corollary, proof, solution from LaTeX content.
    Associate proofs with the preceding theorem/proposition.
    """
    environments = ['definition', 'lemma', 'proposition', 'theorem', 'corollary']
    extracted = []

    # Split content into parts, handling both \begin{env} and %<BLOCK type=env
    parts = re.split(r'(\\(?:begin\{(?:' + '|'.join(environments) + r')\})|%<BLOCK type=(?:' + '|'.join(environments + ['proof']) + r'))', latex_content)

    current_problem = None
    for i in range(1, len(parts), 2):
        env_start = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        if env_start.startswith('\\begin{'):
            env_type = re.search(r'\\begin\{([^}]+)\}', env_start).group(1)
            end_pattern = r'\\end\{' + env_type + r'\}'
        elif env_start.startswith('%<BLOCK type='):
            env_type = re.search(r'%<BLOCK type=([^>\s]+)', env_start).group(1)
            end_pattern = r'%</BLOCK>'
        else:
            continue
        end_match = re.search(end_pattern, content)
        if end_match:
            env_content = content[:end_match.start()].strip()
            if env_type in environments:
                current_problem = {
                    "index": len(extracted) + 1,
                    "problem": env_content,
                    "proof": "",
                    "题目类型": env_type,
                    "预估难度": "",
                    "source": "",
                    "source_index": ""
                }
                extracted.append(current_problem)
            elif env_type == 'proof' and current_problem:
                current_problem["proof"] = env_content
                current_problem = None  # Reset after assigning proof

    return extracted

def call_llm(prompt, api_key, base_url, model):
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
        return content
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None

def extract_implicit_definitions(latex_content, api_key, base_url, model):
    prompt = f"""
请从以下 LaTeX 文本中提取所有隐式的定义（definition），包括没有明确标记为 definition 的部分，以及在其他环境中（如 proposition、theorem）中包含定义性内容的段落。
隐式的定义可能以 "Let us define"、"We define"、"Define"、"Let us identify"、"We write ... as" 等开头的句子或段落，或者描述概念、符号、函数、比率等的定义性内容。

例如：
- "Let us identify p with its coefficient vector" 这样的句子。
- "We write the Crouzeix ratio as f(c,A) = τ(c,A)/β(c,A)" 这样的定义。
- "We can rewrite τ as τ(c,A) = max{{|q(c,z)|:z ∈ W(A)}}" 这样的重写定义。

返回 JSON 格式的列表，每个元素包含：
- "problem": 定义内容（包括相关数学表达式）
- "proof": 如果有相关证明则填写，否则空字符串
- "题目类型": "definition"
- "预估难度": ""
- "source": ""
- "source_index": ""

请确保提取全面，不要遗漏任何潜在的定义。
如果没有找到隐式定义，返回空列表 []。

文本：
{latex_content}

请只返回 JSON 列表，不要其他内容。
"""
    try:
        response = call_llm(prompt, api_key, base_url, model)
        if response is None:
            return []
        # 尝试解析 JSON
        implicit_defs = json.loads(response)
        # 添加 index
        for i, item in enumerate(implicit_defs, start=1):
            item["index"] = i
        return implicit_defs
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"LLM 响应: {response}")
        return []
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return []

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract theorem-like environments from a LaTeX file into JSON.")
    parser.add_argument("input_tex", help="Path to the input .tex file")
    parser.add_argument("output_json", help="Path for the extracted JSON output")
    args = parser.parse_args()

    latex_file = args.input_tex
    output_file = args.output_json

    if not os.path.exists(latex_file):
        print(f"File {latex_file} does not exist.")
        return

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    api_key = config['api_key']
    base_url = config['base_url']
    model = config['model']

    with open(latex_file, 'r', encoding='utf-8') as f:
        latex_content = f.read()

    extracted_data = extract_math_environments(latex_content)

    # Extract implicit definitions using LLM
    implicit_defs = extract_implicit_definitions(latex_content, api_key, base_url, model)
    # Adjust indices for implicit defs
    for item in implicit_defs:
        item["index"] = len(extracted_data) + item["index"]
    extracted_data.extend(implicit_defs)

    # Ensure output directory exists
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    print(f"Extracted data saved to {output_file}")

if __name__ == "__main__":
    main()