import re
import json
import os

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

    with open(latex_file, 'r', encoding='utf-8') as f:
        latex_content = f.read()

    extracted_data = extract_math_environments(latex_content)

    # Ensure output directory exists
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    print(f"Extracted data saved to {output_file}")

if __name__ == "__main__":
    main()