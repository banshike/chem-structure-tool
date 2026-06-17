"""测试 DeepSeek 对不同 prompt 的响应"""
import requests, json, os

api_key = os.environ.get('DEEPSEEK_API_KEY', '')

url = 'https://api.deepseek.com/chat/completions'

# 当前项目的 prompt
prompt_current = """You are a chemistry nomenclature expert. Your ONLY job is to translate chemical names into standard IUPAC systematic names.
Rules:
1. If the input is a common/trivial name, output the IUPAC systematic name.
2. Output ONLY the IUPAC name on a single line. No explanations.
3. If you cannot determine the IUPAC name, output UNKNOWN."""

# 宽松 prompt - 直接输出 SMILES
prompt_smiles = """You are a chemistry expert. Given a chemical description, output the SMILES string of the described compound. Output ONLY the SMILES string, nothing else. If you cannot determine it, output UNKNOWN."""

# 改进 prompt - 描述性输入处理
prompt_improved = """You are a chemistry expert. Your job is to understand chemical descriptions and output the corresponding compound information.

Rules:
1. If input is a chemical NAME (e.g., "aspirin", "水杨酸"), output its IUPAC name.
2. If input describes a CHEMICAL REACTION or product (e.g., "A和B成的酯"), figure out the product and output its IUPAC systematic name.
3. Output ONLY the IUPAC name on a single line. No explanations.
4. If you cannot determine it, output UNKNOWN."""

tests = [
    ("当前项目的prompt（仅IUPAC名）", prompt_current),
    ("宽松prompt（直接输出SMILES）", prompt_smiles),
    ("改进prompt（支持描述性输入）", prompt_improved),
]

for label, prompt in tests:
    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': '乙酰水杨酸和水杨酸成的酯'}
        ],
        'max_tokens': 200,
        'temperature': 0.0,
    }
    try:
        r = requests.post(url, json=payload, headers={'Authorization': f'Bearer {api_key}'}, timeout=15)
        if r.status_code == 200:
            content = r.json()['choices'][0]['message']['content']
            print(f'[{label}]')
            print(f'  返回: {content}\n')
        else:
            print(f'[{label}] API错误: {r.status_code}\n')
    except Exception as e:
        print(f'[{label}] 异常: {e}\n')
