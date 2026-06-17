"""
============================================================
ChemStructure Tool — 化学描述推理模块
将自然语言化学描述（如反应产物、结构描述）推理为 SMILES
============================================================
"""

import json
import logging
import os
import re
import requests
from typing import Optional, Dict

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_MAX_TOKENS,
    DEEPSEEK_TEMPERATURE,
)

logger = logging.getLogger(__name__)


# ── Prompt 模板 ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are a chemistry structure reasoning expert. Your job is to understand chemical descriptions and output the corresponding SMILES string.

You can handle:
1. Chemical NAMES → output SMILES (e.g., "aspirin" → "CC(=O)Oc1ccccc1C(=O)O")
2. Chemical DESCRIPTIONS → reason and output SMILES
   - "A和B形成的酯" → figure out the esterification product
   - "A与B的反应产物" → figure out the reaction product
   - "A的B取代物" → figure out the substituted product
3. CHINESE names → output SMILES (e.g., "水杨酸" → "Oc1ccccc1C(=O)O")

Rules:
- Output ONLY the SMILES string on a single line. No explanations, no prefixes.
- Make sure the SMILES is valid and represents a real chemical structure.
- If the description is ambiguous, choose the most chemically reasonable interpretation.
- If you cannot determine the SMILES, output "UNKNOWN".
- DO NOT output IUPAC names, ONLY output SMILES.

Examples:
- 乙酰水杨酸和水杨酸成的酯 → CC(=O)Oc1ccccc1C(=O)Oc2ccccc2C(=O)O
- 乙醇和乙酸形成的酯 → CCOC(C)=O
- 苯的硝基取代物 → O=N(=O)c1ccccc1
- 水杨酸 → Oc1ccccc1C(=O)O
- 维生素C → OC[C@@H](O)[C@H]1OC(=O)C(O)=C1O
"""


def _get_api_key() -> str:
    """读取 API Key"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    return DEEPSEEK_API_KEY.strip()


def _is_descriptive_input(user_input: str) -> bool:
    """
    判断用户输入是否为描述性文本（而非标准化学名称）。
    检测特征：包含反应描述词、中文描述、非标准命名模式。
    """
    # 如果已经是有效 SMILES，不需要推理
    if re.match(r'^[A-Za-z0-9@+\-\[\]\(\)\\\/%=#$,.]+$', user_input):
        return False

    # 检测描述性关键词
    desc_patterns = [
        r'[和与及]',       # "A和B" "A与B"
        r'成[的酯]',        # "成的酯"
        r'反[应]',          # "反应"
        r'取[代]',          # "取代"
        r'形[成]',          # "形成"
        r'生[成]',          # "生成"
        r'脱[水]',          # "脱水"
        r'酯[化]',          # "酯化"
        r'加[成]',          # "加成"
        r'聚[合]',          # "聚合"
        r'产物',            # "产物"
        r'衍[生物]',        # "衍生物"
    ]
    
    for pattern in desc_patterns:
        if re.search(pattern, user_input):
            return True

    # 纯中文且超过 3 个字 → 可能是描述
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', user_input)
    if len(chinese_chars) >= 4 and len(chinese_chars) / max(len(user_input), 1) > 0.5:
        # 检查是否可能是已知的化学中文名（通过 PubChem 可查）
        # 短中文名可能是标准名称，长中文描述更需要推理
        if len(user_input) > 6:
            return True

    return False


def resolve_description(user_input: str) -> Optional[Dict]:
    """
    将化学描述性输入推理为 SMILES。
    
    Args:
        user_input: 用户的描述性输入（如"乙酰水杨酸和水杨酸成的酯"）
    
    Returns:
        {
            "smiles": "...",
            "source": "LLM-Description",
            "description": "推理说明（可选）"
        }
        失败返回 None
    """
    if not _get_api_key():
        logger.info("DEEPSEEK_API_KEY 未设置，跳过描述推理")
        return None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input.strip()},
    ]

    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": 300,  # 描述推理需要更多 tokens
        "temperature": DEEPSEEK_TEMPERATURE,
        # 关闭思考模式，避免 tokens 被推理消耗
        "thinking": {"type": "disabled"},
    }

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning("DeepSeek API returned %d: %s", resp.status_code, resp.text[:200])
            return None

        data = resp.json()

        if "error" in data:
            logger.warning("DeepSeek API error: %s", data["error"])
            return None

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        if not content:
            logger.warning("DeepSeek response has no content")
            return None

        # 提取 SMILES（取第一行，去空白和引号）
        smiles = content.strip().split("\n")[0].strip().strip('"').strip("'")

        if not smiles or smiles.upper() == "UNKNOWN" or len(smiles) < 2:
            return None

        # 用 RDKit 验证 SMILES 是否有效
        try:
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.warning("DeepSeek 推理出的 SMILES 无效: %s", smiles)
                return None
            # 规范化 SMILES
            canonical_smiles = Chem.MolToSmiles(mol)
        except ImportError:
            # 没有 RDKit 时信任 DeepSeek 的输出
            canonical_smiles = smiles
        except Exception as e:
            logger.warning("RDKit 验证失败: %s", e)
            return None

        return {
            "smiles": canonical_smiles,
            "source": "LLM-Description",
            "raw_smiles": smiles,
        }

    except requests.exceptions.Timeout:
        logger.warning("DeepSeek API request timed out")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("DeepSeek API connection failed")
        return None
    except Exception as e:
        logger.warning("DeepSeek description resolver error: %s", e)
        return None
