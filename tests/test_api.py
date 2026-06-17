"""
============================================================
ChemStructure Tool — API 测试脚本
测试所有核心功能：文本解析、2D/3D渲染、导出等
============================================================
"""

import sys
import os
import json
import time
import requests
from typing import Dict, List, Tuple

# ── 配置 ────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:5000"
API_URL = f"{BASE_URL}/api"

# 测试用例列表
TEST_CASES = {
    "smiles": {
        "label": "SMILES 直接解析",
        "inputs": [
            # (输入, 预期包含的分子式或分子量)
            ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", ["C8H10N4O2", "194.19"]),
            ("CC(=O)O", ["C2H4O2", "60.05"]),
            ("CCO", ["C2H6O", "46.07"]),
            ("c1ccccc1", ["C6H6", "78.11"]),
        ]
    },
    "iupac": {
        "label": "IUPAC 命名 (OPSIN)",
        "inputs": [
            ("propan-2-one", ["C3H6O", "58.08"]),
            ("ethanoic acid", ["C2H4O2", "60.05"]),
            ("benzene", ["C6H6", "78.11"]),
            ("methanol", ["CH4O", "32.04"]),
        ]
    },
    "formula": {
        "label": "分子式 (PubChem)",
        "inputs": [
            ("C6H12O6", ["C6H12O6", "180.16"]),
            ("H2O", ["H2O", "18.02"]),
            ("NaCl", ["58.44"]),
            ("C8H10N4O2", ["C8H10N4O2", "194.19"]),
        ]
    },
}

# 测试 2D 渲染的 SMILES
RENDER_2D_SMILES = ["CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "CCO", "c1ccccc1", "CC(=O)OC1=CC=CC=C1C(=O)O"]

# 测试导出的 SMILES
EXPORT_SMILES = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
EXPORT_FORMATS = ["MOL", "SDF", "InChI", "SMILES"]


# ── 颜色输出辅助 ──────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_result(name: str, passed: bool, detail: str = ""):
    """格式化输出测试结果"""
    icon = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    msg = f"  {icon} [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def check_server() -> bool:
    """检查服务是否在运行"""
    try:
        r = requests.get(BASE_URL, timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# ── API 调用封装 ────────────────────────────────────────────

def api_process(input_text: str) -> Dict:
    """调用 /api/process 一键处理接口"""
    resp = requests.post(
        f"{API_URL}/process",
        json={"input": input_text},
        timeout=30
    )
    return resp.json()


def api_render_2d(smiles: str, fmt: str = "PNG") -> Dict:
    """调用 /api/render-2d 生成 2D 结构图"""
    resp = requests.post(
        f"{API_URL}/render-2d",
        json={"smiles": smiles, "format": fmt},
        timeout=15
    )
    return resp.json()


def api_render_3d(smiles: str) -> Dict:
    """调用 /api/render-3d 生成 3D 构象"""
    resp = requests.post(
        f"{API_URL}/render-3d",
        json={"smiles": smiles},
        timeout=30
    )
    return resp.json()


def api_molecule_info(smiles: str) -> Dict:
    """调用 /api/molecule-info 获取分子信息"""
    resp = requests.post(
        f"{API_URL}/molecule-info",
        json={"smiles": smiles},
        timeout=10
    )
    return resp.json()


def api_export(smiles: str, fmt: str) -> Dict:
    """调用 /api/export 导出分子"""
    resp = requests.post(
        f"{API_URL}/export",
        json={"smiles": smiles, "format": fmt},
        timeout=10
    )
    return resp.json()


# ── 测试函数 ────────────────────────────────────────────────

def test_text_parsing():
    """测试文本解析功能 (SMILES / IUPAC / 分子式)"""
    passed = 0
    total = 0
    
    print(f"\n{BOLD}{CYAN}📝 文本解析测试{RESET}")
    print("=" * 60)
    
    for category, config in TEST_CASES.items():
        print(f"\n{YELLOW}▶ {config['label']}{RESET}")
        
        for input_text, expected_keywords in config["inputs"]:
            total += 1
            try:
                result = api_process(input_text)
                
                if result.get("success"):
                    smiles = result.get("smiles", "")
                    molecule_info = result.get("molecule_info", {})
                    formula = molecule_info.get("formula", "")
                    mw = str(molecule_info.get("molecular_weight", ""))
                    source = result.get("source", "?")
                    
                    # 检查预期关键词是否出现在结果中
                    all_found = True
                    missing = []
                    for kw in expected_keywords:
                        found = kw in formula or kw in mw or kw in smiles or kw in str(result)
                        if not found:
                            # 不区分大小写再试一次
                            found = kw.lower() in str(result).lower()
                        if not found:
                            all_found = False
                            missing.append(kw)
                    
                    detail = f"来源: {source}, SMILES: {smiles[:40]}..."
                    if not all_found:
                        detail += f" | 缺少预期: {missing}"
                    
                    print_result(f"\"{input_text}\" → \"{smiles[:30]}...\"", all_found, detail)
                    if all_found:
                        passed += 1
                else:
                    error = result.get("error", "未知错误")
                    print_result(f"\"{input_text}\"", False, f"API 返回失败: {error}")
                    
            except requests.exceptions.Timeout:
                print_result(f"\"{input_text}\"", False, "请求超时")
            except Exception as e:
                print_result(f"\"{input_text}\"", False, f"异常: {e}")
    
    return passed, total


def test_2d_rendering():
    """测试 2D 结构图渲染"""
    print(f"\n{BOLD}{CYAN}🔬 2D 结构图渲染测试{RESET}")
    print("=" * 60)
    
    passed = 0
    total = len(RENDER_2D_SMILES) * 2  # PNG + SVG
    
    for smiles in RENDER_2D_SMILES:
        # 测试 PNG
        try:
            result = api_render_2d(smiles, "PNG")
            if result.get("success") and result.get("image_base64"):
                img_len = len(result["image_base64"])
                print_result(f"PNG: {smiles[:25]}...", True, f"Base64 长度: {img_len}")
                passed += 1
            else:
                print_result(f"PNG: {smiles[:25]}...", False, result.get("error", "未知错误"))
        except Exception as e:
            print_result(f"PNG: {smiles[:25]}...", False, str(e))
        
        # 测试 SVG
        try:
            result = api_render_2d(smiles, "SVG")
            if result.get("success") and result.get("image_base64"):
                import base64
                svg_text = base64.b64decode(result["image_base64"]).decode("utf-8")
                has_svg_tag = "<svg" in svg_text
                print_result(f"SVG: {smiles[:25]}...", has_svg_tag, f"包含 SVG 标签: {has_svg_tag}")
                if has_svg_tag:
                    passed += 1
            else:
                print_result(f"SVG: {smiles[:25]}...", False, result.get("error", "未知错误"))
        except Exception as e:
            print_result(f"SVG: {smiles[:25]}...", False, str(e))
    
    return passed, total


def test_3d_rendering():
    """测试 3D 构象生成"""
    print(f"\n{BOLD}{CYAN}🧬 3D 构象生成测试{RESET}")
    print("=" * 60)
    
    test_smiles = ["CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "CCO", "c1ccccc1"]
    passed = 0
    total = len(test_smiles)
    
    for smiles in test_smiles:
        try:
            result = api_render_3d(smiles)
            if result.get("success") and result.get("pdb_data"):
                pdb = result["pdb_data"]
                has_atoms = "ATOM" in pdb or "HETATM" in pdb
                has_ends = "END" in pdb
                atom_count = pdb.count("ATOM") + pdb.count("HETATM")
                detail = f"ATOM 记录: {atom_count}, END: {has_ends}"
                print_result(f"3D: {smiles[:25]}...", has_atoms, detail)
                if has_atoms:
                    passed += 1
            else:
                print_result(f"3D: {smiles[:25]}...", False, result.get("error", "未知错误"))
        except Exception as e:
            print_result(f"3D: {smiles[:25]}...", False, str(e))
    
    return passed, total


def test_molecule_info():
    """测试分子信息查询"""
    print(f"\n{BOLD}{CYAN}📋 分子信息查询测试{RESET}")
    print("=" * 60)
    
    test_cases = [
        ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", ["C8H10N4O2", "194.19", "formula", "molecular_weight"]),
        ("CCO", ["C2H6O", "46.07"]),
    ]
    passed = 0
    total = len(test_cases)
    
    for smiles, expected in test_cases:
        try:
            result = api_molecule_info(smiles)
            if result.get("success"):
                info = result.get("molecule_info", {})
                validation = result.get("validation", {})
                
                # 检查信息完整性
                has_formula = bool(info.get("formula"))
                has_mw = bool(info.get("molecular_weight"))
                has_valid = validation.get("valid", False)
                
                all_ok = has_formula and has_mw and has_valid
                detail = f"分子式: {info.get('formula','?')}, 分子量: {info.get('molecular_weight','?')}, 校验: {has_valid}"
                print_result(f"信息查询: {smiles[:25]}...", all_ok, detail)
                if all_ok:
                    passed += 1
            else:
                print_result(f"信息查询: {smiles[:25]}...", False, result.get("error", "未知错误"))
        except Exception as e:
            print_result(f"信息查询: {smiles[:25]}...", False, str(e))
    
    return passed, total


def test_export():
    """测试多格式导出"""
    print(f"\n{BOLD}{CYAN}📦 多格式导出测试{RESET}")
    print("=" * 60)
    
    passed = 0
    total = len(EXPORT_FORMATS)
    
    for fmt in EXPORT_FORMATS:
        try:
            result = api_export(EXPORT_SMILES, fmt)
            if result.get("success") and result.get("data"):
                data = result["data"]
                detail = f"数据长度: {len(data)} 字符"
                print_result(f"导出 {fmt}: {EXPORT_SMILES[:20]}...", True, detail)
                passed += 1
            else:
                print_result(f"导出 {fmt}", False, result.get("error", "未知错误"))
        except Exception as e:
            print_result(f"导出 {fmt}", False, str(e))
    
    return passed, total


def test_error_handling():
    """测试错误处理"""
    print(f"\n{BOLD}{CYAN}⚠️  错误处理测试{RESET}")
    print("=" * 60)
    
    test_cases = [
        ("", "empty", "应为 400/失败"),
        ("ZZZZZZinvalid", "invalid_smiles", "应为 400/失败"),
        ("!@#$%", "special_chars", "应为 400/失败"),
    ]
    passed = 0
    total = len(test_cases)
    
    for input_text, case_name, expected in test_cases:
        try:
            result = api_process(input_text)
            if not result.get("success"):
                error = result.get("error", "")
                print_result(f"错误处理 [{case_name}]: \"{input_text}\"", True, f"正确拒绝: {error[:60]}")
                passed += 1
            else:
                print_result(f"错误处理 [{case_name}]: \"{input_text}\"", False, "意外返回成功")
        except requests.exceptions.Timeout:
            print_result(f"错误处理 [{case_name}]", True, "超时（可接受）")
            passed += 1
        except Exception as e:
            print_result(f"错误处理 [{case_name}]", False, str(e))
    
    return passed, total


def test_batch_performance():
    """批量性能测试"""
    print(f"\n{BOLD}{CYAN}⚡ 批量性能测试{RESET}")
    print("=" * 60)
    
    batch = [
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # 咖啡因
        "CCO",                              # 乙醇
        "c1ccccc1",                         # 苯
        "CC(=O)O",                          # 乙酸
        "CC(=O)OC1=CC=CC=C1C(=O)O",        # 阿司匹林
        "propan-2-one",                     # 丙酮 (OPSIN)
        "methanol",                         # 甲醇 (OPSIN)
        "H2O",                              # 水 (PubChem)
    ]
    
    start = time.time()
    success = 0
    
    for i, input_text in enumerate(batch, 1):
        try:
            result = api_process(input_text)
            if result.get("success"):
                success += 1
                elapsed = time.time() - start
                print(f"  [{i}/{len(batch)}] ✅ {str(result.get('smiles',''))[:30]}... "
                      f"(来源: {result.get('source','?')}, {elapsed:.1f}s)")
            time.sleep(0.3)  # 礼貌性间隔
        except Exception as e:
            elapsed = time.time() - start
            print(f"  [{i}/{len(batch)}] ❌ {input_text[:20]}... ({elapsed:.1f}s) - {e}")
    
    total_time = time.time() - start
    passed = success
    total = len(batch)
    
    print(f"  {YELLOW}⏱  总耗时: {total_time:.2f}s, 平均: {total_time/max(1,len(batch)):.2f}s/请求{RESET}")
    
    return passed, total


# ── 主函数 ──────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  ChemStructure Tool -- 全功能测试套件{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")
    
    # 检查服务状态
    print(f"{CYAN}🔍 检查服务状态...{RESET}")
    if not check_server():
        print(f"{RED}❌ 服务未运行！请先启动: cd chem-structure-tool-master && python app.py{RESET}")
        sys.exit(1)
    print(f"{GREEN}✅ 服务运行正常: {BASE_URL}{RESET}\n")
    
    total_passed = 0
    total_tests = 0
    all_results = []
    
    # 运行所有测试
    test_functions = [
        ("📝 文本解析", test_text_parsing),
        ("🔬 2D 渲染", test_2d_rendering),
        ("🧬 3D 渲染", test_3d_rendering),
        ("📋 分子信息", test_molecule_info),
        ("📦 导出测试", test_export),
        ("⚠️  错误处理", test_error_handling),
        ("⚡ 批量性能", test_batch_performance),
    ]
    
    for name, func in test_functions:
        try:
            p, t = func()
            total_passed += p
            total_tests += t
            all_results.append((name, p, t))
        except Exception as e:
            print(f"{RED}❌ 测试组 '{name}' 执行异常: {e}{RESET}")
    
    # ── 汇总报告 ──
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  📊 测试汇总{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    
    for name, p, t in all_results:
        if t > 0:
            bar = "█" * int(p / t * 30) + "░" * (30 - int(p / t * 30))
            pct = p / t * 100
            color = GREEN if pct == 100 else (YELLOW if pct >= 50 else RED)
            print(f"  {name:12s} {color}{p:3d}/{t:<3d}{RESET} ({pct:5.1f}%) {bar}")
    
    total_pct = total_passed / total_tests * 100 if total_tests > 0 else 0
    overall_color = GREEN if total_pct == 100 else (YELLOW if total_pct >= 50 else RED)
    
    print(f"\n  {'=' * 40}")
    print(f"  {BOLD}总计: {overall_color}{total_passed}/{total_tests}{RESET} 测试通过 ({total_pct:.1f}%)")
    
    if total_passed == total_tests:
        print(f"\n  {GREEN}{BOLD}🎉 全部测试通过！{RESET}")
    else:
        print(f"\n  {YELLOW}⚠️  部分测试未通过，请检查详情{RESET}")
    
    print()


if __name__ == "__main__":
    main()
