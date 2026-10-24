"""
verify_article.py —— 文章数据一致性自检
=======================================
检查文章里引用的每个关键数字，是否能在 results/*.json 里找到对应。
用于投稿前确认"文章说的"和"代码跑出的"一致。

用法：
    python verify_article.py
"""
import json
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)  # money1
RES = os.path.join(ROOT, "results")
ARTICLE = os.path.join(ROOT, "article-final.md")


def load(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check(label, actual, expected, tol=0.002):
    """比较数值。"""
    if actual is None:
        return ("FAIL", f"{label}: 数据缺失")
    ok = abs(float(actual) - float(expected)) <= tol
    return ("PASS" if ok else "FAIL",
            f"{label}: 文章 {expected} vs 数据 {actual}")


def main():
    print("=" * 80)
    print("文章数据一致性自检")
    print("=" * 80)

    results = []
    article = open(ARTICLE, encoding="utf-8").read() if os.path.exists(ARTICLE) else ""

    # ---------- E1: 载体 ----------
    e1 = load("exp01_e1_carriers.json")
    if e1:
        carriers = {c["name"]: c for c in e1["carriers"]}
        base = e1["base_tokens"]
        results.append(check("基准载荷 tokens", base, 22))
        # 关键载体
        for name, exp_tpc in [
            ("diluted", 0.153), ("plain", 0.216), ("tag_partial", 0.216),
            ("zero_width_full", 0.931), ("tag_full", 3.000), ("vs_full", 3.971),
            ("fullwidth", 1.755), ("zero_width_binary", 0.987),
        ]:
            if name in carriers:
                results.append(check(f"载体 {name} 的 token/char",
                                     carriers[name]["token_per_char"], exp_tpc))

    # ---------- E2: 基线 ----------
    e2 = load("exp01_e2_baseline.json")
    if e2:
        ov = e2["overall"]
        results.append(check("正常文本均值", ov["mean"], 0.761, 0.005))
        results.append(check("正常文本中位", ov["median"], 0.801, 0.005))
        results.append(check("正常文本 P90", ov["p90"], 1.223, 0.005))
        results.append(check("正常文本 P95", ov["p95"], 1.364, 0.005))
        results.append(check("正常文本 P99", ov["p99"], 1.551, 0.005))
        results.append(check("正常文本 Max", ov["max"], 1.750, 0.005))
        results.append(check("正常文本条数", ov["n"], 230, 0))

        by_cat = e2["by_category"]
        for cat, exp_mean in [("short", 1.257), ("zh_tech", 1.112),
                              ("en_tech", 0.158), ("mixed", 0.683)]:
            if cat in by_cat:
                results.append(check(f"类别 {cat} 均值",
                                     by_cat[cat]["mean"], exp_mean, 0.005))

    # ---------- E3: 检测器 ----------
    e3 = load("exp01_e3_roc.json")
    if e3:
        d4_auc = e3.get("_d4_roc", {}).get("auc")
        results.append(check("D4 AUC", d4_auc, 0.5389, 0.005))
        for dk, exp_tpr, exp_fpr in [
            ("D4_token_inflate", 0.438, 0.474),
            ("D3_zw_density", 0.250, 0.000),
            ("D6_hardened", 0.562, 0.026),
        ]:
            if dk in e3:
                results.append(check(f"{dk} TPR", e3[dk]["tpr"], exp_tpr, 0.01))
                results.append(check(f"{dk} FPR", e3[dk]["fpr"], exp_fpr, 0.01))

    # ---------- E4: 对抗性 ----------
    e4 = load("exp01_e4_adversarial.json")
    if e4:
        bypassed = sum(1 for r in e4 if not r["d4"])
        results.append(check("D4 被绕过数量", bypassed, 12, 0))
        results.append(check("对抗策略总数", len(e4), 12, 0))

    # ---------- E5: 分层 ----------
    e5 = load("exp02_e5_stratified.json")
    if e5:
        auc_by = e5.get("auc_by_lang", {})
        results.append(check("中文 AUC", auc_by.get("zh"), 0.2758, 0.005))
        results.append(check("英文 AUC", auc_by.get("en"), 0.8243, 0.005))
        results.append(check("混排 AUC", auc_by.get("mixed"), 0.5208, 0.005))

    # ---------- E6: 特征 ----------
    e6 = load("exp02_e6_features.json")
    if e6:
        results.append(check("token_per_char AUC", e6["token_per_char"]["auc"], 0.5389, 0.005))
        results.append(check("invisible_ratio AUC", e6["invisible_ratio"]["auc"], 0.6250, 0.005))

    # ---------- E7: 组合 ----------
    e7 = load("exp02_e7_combined.json")
    if e7:
        lay = e7["layered"]
        tpr = lay["tp"] / lay["n_pos"]
        fpr = lay["fp"] / lay["n_neg"]
        results.append(check("分层检测器 TPR", tpr, 0.688, 0.01))
        results.append(check("分层检测器 FPR", fpr, 0.052, 0.01))

    # ---------- E8-E11: 多 tokenizer ----------
    e8 = load("exp03_multi_tokenizer.json")
    if e8:
        zh_sample = e8.get("e8_zh_sample", {})
        results.append(check("中文样本 cl100k tokens", zh_sample.get("cl100k_base"), 48, 0))
        results.append(check("中文样本 o200k tokens", zh_sample.get("o200k_base"), 31, 0))
        results.append(check("中文样本 p50k tokens", zh_sample.get("p50k_base"), 94, 0))

        aucs = e8.get("e9_auc_by_tokenizer", {})
        for tok, exp_zh, exp_en in [
            ("cl100k_base", 0.2931, 0.8505),
            ("o200k_base", 0.4942, 0.8489),
            ("p50k_base", 0.2555, 0.8291),
            ("r50k_base", 0.2555, 0.8283),
        ]:
            if tok in aucs:
                results.append(check(f"{tok} 中文 AUC", aucs[tok].get("zh"), exp_zh, 0.005))
                results.append(check(f"{tok} 英文 AUC", aucs[tok].get("en"), exp_en, 0.005))

        base = e8.get("e10_baseline", {})
        for tok, exp_zh_mean in [("cl100k_base", 1.117), ("o200k_base", 0.744),
                                  ("p50k_base", 2.049)]:
            if tok in base:
                results.append(check(f"{tok} 中文均值", base[tok]["zh_mean"], exp_zh_mean, 0.005))

    # ---------- 文章结构检查 ----------
    print("\n" + "-" * 80)
    print("文章结构检查")
    print("-" * 80)

    # 章节编号顺序
    nums = []
    for m in re.finditer(r"^## (\d+)\.", article, re.M):
        nums.append(int(m.group(1)))
    ordered = nums == sorted(nums)
    results.append(("PASS" if ordered else "FAIL",
                    f"章节编号顺序: {nums}"))
    results.append(("PASS" if len(set(nums)) == len(nums) else "FAIL",
                    f"章节编号无重复: {'是' if len(set(nums))==len(nums) else '否'}"))

    # 仓库链接
    has_repo = "https://github.com/zh123-zh316/token-inflation-detector-eval" in article
    results.append(("PASS" if has_repo else "FAIL", f"包含仓库链接: {has_repo}"))

    # 字数
    cn_chars = len(re.findall(r"[\u4e00-\u9fa5]", article))
    results.append(("PASS" if 3000 <= cn_chars <= 8000 else "WARN",
                    f"中文字数: {cn_chars}"))

    # 数据引用标注
    refs = len(re.findall(r"results/exp\d+_\w+\.json", article))
    results.append(("PASS" if refs >= 5 else "WARN", f"数据文件引用数: {refs}"))

    # ---------- 输出 ----------
    print()
    passed = failed = warned = 0
    for status, msg in results:
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}[status]
        print(f"  {icon} {msg}")
        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            warned += 1

    print("\n" + "=" * 80)
    print(f"结果：{passed} 通过，{failed} 失败，{warned} 警告")
    print("=" * 80)

    if failed:
        print("\n[!] 有失败项，投稿前必须修正。")
        return 1
    print("\n[OK] 所有关键数据与文章一致，可以投稿。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
