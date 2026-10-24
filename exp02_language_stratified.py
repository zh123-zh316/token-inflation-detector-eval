"""
exp02_language_stratified.py —— 分层实验（补救 E1-E4 的缺陷）
=============================================================
E2 发现了关键问题：正常文本的 token/char 是双峰的（英文 0.16，中文 1.2+）。
这导致全局阈值不可能同时覆盖两种语言。

本实验：
    E5 按语言分层，分别计算 token 膨胀检测的 AUC
    E6 跨语言误报分析（用中文阈值去检测英文，会怎样）
    E7 与"中文友好"的替代特征对比（字节长度比、Unicode 块占比）
"""
import json
import os
import sys
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "results")
os.makedirs(OUT, exist_ok=True)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        matplotlib.rcParams["font.sans-serif"] = [f]
        matplotlib.rcParams["axes.unicode_minus"] = False
        break
    except Exception:
        continue

from corpus import get_corpus
from carriers import get_carriers
from detectors import count_tokens, token_per_char, score_all

CORPUS = get_corpus()
CARRIERS = get_carriers()


def script_of(text):
    """判断文本主脚本。"""
    cjk = sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)
    lat = sum(1 for c in text if "a" <= c.lower() <= "z")
    if cjk > lat * 2:
        return "zh"
    if lat > cjk * 2:
        return "en"
    return "mixed"


def bytes_per_char(text):
    return len(text.encode("utf-8")) / len(text) if text else 0


def non_ascii_ratio(text):
    if not text:
        return 0.0
    return sum(1 for c in text if ord(c) > 127) / len(text)


# ============================================================
# E5: 按语言分层
# ============================================================

def e5_stratified():
    print("\n" + "=" * 90)
    print("E5: 按语言分层 —— token 膨胀检测是否在单语种内有效？")
    print("=" * 90)

    # 负样本按语言分组
    neg_by_lang = defaultdict(list)
    for cat, text in CORPUS:
        neg_by_lang[script_of(text)].append(token_per_char(text))

    # 正样本按载体类型分组
    pos_ascii = []   # ASCII 类载体（Tag、零宽等，不改变语言）
    pos_other = []
    for cid, name, desc, text in CARRIERS:
        if cid == "C01":
            continue
        tpc = token_per_char(text)
        if script_of(text) == "en" or non_ascii_ratio(text) < 0.5:
            pos_ascii.append((name, tpc))
        else:
            pos_other.append((name, tpc))

    print(f"\n正常文本按语言分组：")
    for lang, vals in neg_by_lang.items():
        arr = np.array(vals)
        print(f"  {lang:8s} n={len(arr):3d}  均值={arr.mean():.3f}  "
              f"P95={np.percentile(arr,95):.3f}  Max={arr.max():.3f}")

    # 分语言计算 AUC
    print(f"\n--- 分语言 AUC（正样本 = 全部 16 种载体）---")
    pos_all = np.array([token_per_char(t) for _, _, _, t in CARRIERS if _ != "C01"])
    auc_results = {}
    for lang, vals in neg_by_lang.items():
        neg = np.array(vals)
        if len(neg) < 5:
            continue
        # AUC
        sorted_neg = np.sort(neg)
        auc = 0.0
        for p in pos_all:
            auc += (sorted_neg < p).sum() + 0.5 * (sorted_neg == p).sum()
        auc /= (len(pos_all) * len(neg))
        auc_results[lang] = round(auc, 4)
        print(f"  {lang:8s} AUC={auc:.4f}  (n_neg={len(neg)})")

    # 只用 ASCII 载体（更公平的对比）
    print(f"\n--- 分语言 AUC（正样本 = 仅 ASCII 类载体，排除中英混排影响）---")
    pos_ascii_arr = np.array([v for _, v in pos_ascii])
    for lang, vals in neg_by_lang.items():
        neg = np.array(vals)
        if len(neg) < 5:
            continue
        sorted_neg = np.sort(neg)
        auc = 0.0
        for p in pos_ascii_arr:
            auc += (sorted_neg < p).sum() + 0.5 * (sorted_neg == p).sum()
        auc /= (len(pos_ascii_arr) * len(neg))
        print(f"  {lang:8s} AUC={auc:.4f}")

    with open(os.path.join(OUT, "exp02_e5_stratified.json"), "w", encoding="utf-8") as f:
        json.dump({"auc_by_lang": auc_results,
                   "neg_by_lang": {k: [float(x) for x in v] for k, v in neg_by_lang.items()}},
                  f, ensure_ascii=False, indent=1)
    return neg_by_lang, pos_ascii


# ============================================================
# E6: 替代特征对比
# ============================================================

def e6_alternative_features():
    print("\n" + "=" * 90)
    print("E6: 替代特征 —— 有没有比 token/char 更好的语言无关特征？")
    print("=" * 90)

    features = {
        "token_per_char": token_per_char,
        "bytes_per_char": bytes_per_char,
        "non_ascii_ratio": non_ascii_ratio,
        "invisible_ratio": lambda t: score_all(t)["zw_ratio"],
        "has_tag_block": lambda t: 1.0 if score_all(t)["has_tag"] else 0.0,
        "script_mixing": lambda t: 1.0 if score_all(t)["script_mix"] else 0.0,
    }

    pos_texts = [t for cid, _, _, t in CARRIERS if cid != "C01"]
    neg_texts = [t for _, t in CORPUS]

    print(f"\n{'特征':<20} {'AUC':>8} {'最佳阈值':>10} {'TPR':>8} {'FPR':>8}")
    print("-" * 60)

    results = {}
    for fname, fn in features.items():
        pos_vals = np.array([fn(t) for t in pos_texts])
        neg_vals = np.array([fn(t) for t in neg_texts])

        # AUC（假设越大越可疑）
        sorted_neg = np.sort(neg_vals)
        auc = 0.0
        for p in pos_vals:
            auc += (sorted_neg < p).sum() + 0.5 * (sorted_neg == p).sum()
        auc /= (len(pos_vals) * len(neg_vals))

        # 如果 AUC < 0.5，说明方向反了，取反
        direction = 1
        if auc < 0.5:
            auc = 1 - auc
            direction = -1

        # 找最优阈值（Youden J）
        all_vals = np.unique(np.concatenate([pos_vals, neg_vals]))
        best = (0, 0, 0)
        for th in all_vals:
            if direction == 1:
                tp = (pos_vals > th).sum()
                fp = (neg_vals > th).sum()
            else:
                tp = (pos_vals <= th).sum()
                fp = (neg_vals <= th).sum()
            tpr = tp / len(pos_vals)
            fpr = fp / len(neg_vals)
            j = tpr - fpr
            if j > best[0]:
                best = (j, tpr, fpr)
                best_th = th

        results[fname] = {"auc": round(auc, 4), "best_th": float(best_th),
                          "tpr": round(best[1], 4), "fpr": round(best[2], 4),
                          "direction": direction}
        print(f"{fname:<20} {auc:>8.4f} {best_th:>10.3f} "
              f"{best[1]:>7.1%} {best[2]:>7.1%}")

    with open(os.path.join(OUT, "exp02_e6_features.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    return results


# ============================================================
# E7: 组合特征
# ============================================================

def e7_combined():
    print("\n" + "=" * 90)
    print("E7: 组合检测器 —— 结构特征 + 语言分层")
    print("=" * 90)

    def detect_layered(text):
        """分层策略：先看结构特征（语言无关），再看语言内膨胀。"""
        s = score_all(text)
        # 1. 结构特征（绝对确定性，语言无关）
        if s["has_tag"] or s["has_vs"] or s["bidi"] > 0:
            return True
        if s["zw_ratio"] > 0.02:
            return True
        if s["script_mix"]:
            return True
        # 2. 语言内膨胀（仅当文本是纯 ASCII 时才有意义）
        if non_ascii_ratio(text) < 0.1:
            # 纯 ASCII：正常应在 0.15-0.5
            if s["token_per_char"] > 0.7:
                return True
        return False

    pos_texts = [t for cid, _, _, t in CARRIERS if cid != "C01"]
    neg_texts = [t for _, t in CORPUS]

    tp = sum(1 for t in pos_texts if detect_layered(t))
    fp = sum(1 for t in neg_texts if detect_layered(t))

    print(f"\n分层检测器结果：")
    print(f"  检出：{tp}/{len(pos_texts)} = {tp/len(pos_texts):.1%}")
    print(f"  误报：{fp}/{len(neg_texts)} = {fp/len(neg_texts):.1%}")

    missed = [name for cid, name, _, t in CARRIERS if cid != "C01" and not detect_layered(t)]
    print(f"  漏掉的载体：{missed}")

    false_pos = [f"[{cat}] {t[:40]}" for cat, t in CORPUS if detect_layered(t)][:10]
    if false_pos:
        print(f"  误报样本（前10）：")
        for fp_s in false_pos:
            print(f"    {fp_s}")

    # 对比：全局阈值（D4）
    from detectors import detect_d4_token_inflation
    tp_d4 = sum(1 for t in pos_texts if detect_d4_token_inflation(t))
    fp_d4 = sum(1 for t in neg_texts if detect_d4_token_inflation(t))
    print(f"\n对比 D4（全局 token 膨胀阈值 0.85）：")
    print(f"  检出：{tp_d4}/{len(pos_texts)} = {tp_d4/len(pos_texts):.1%}")
    print(f"  误报：{fp_d4}/{len(neg_texts)} = {fp_d4/len(neg_texts):.1%}")

    with open(os.path.join(OUT, "exp02_e7_combined.json"), "w", encoding="utf-8") as f:
        json.dump({"layered": {"tp": tp, "fp": fp, "n_pos": len(pos_texts), "n_neg": len(neg_texts),
                               "missed": missed},
                   "d4_global": {"tp": tp_d4, "fp": fp_d4}}, f, ensure_ascii=False, indent=1)
    return tp, fp


# ============================================================
# 出图
# ============================================================

def make_figures(neg_by_lang, e6_results):
    # 图6：分语言分布对比
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"zh": "#e74c3c", "en": "#3498db", "mixed": "#2ecc71"}
    for lang, vals in neg_by_lang.items():
        ax.hist(vals, bins=25, alpha=0.6, label=f"{lang} (n={len(vals)})",
                color=colors.get(lang, "#95a5a6"))
    ax.set_xlabel("token / char 比值")
    ax.set_ylabel("文本数量")
    ax.set_title("图6 · 正常文本的 token/char 分布 —— 按语言分层后是分离的双峰")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig6_language_stratified.png"), dpi=150)
    plt.close()
    print("  已保存 fig6_language_stratified.png")

    # 图7：特征 AUC 对比
    fig, ax = plt.subplots(figsize=(9, 5))
    names = list(e6_results.keys())
    aucs = [e6_results[n]["auc"] for n in names]
    cols = ["#2ecc71" if a > 0.8 else "#f39c12" if a > 0.6 else "#e74c3c" for a in aucs]
    bars = ax.barh(names, aucs, color=cols)
    ax.axvline(0.5, color="black", linestyle="--", label="随机 (0.5)")
    ax.axvline(0.8, color="green", linestyle=":", label="良好 (0.8)")
    ax.set_xlim(0, 1)
    ax.set_xlabel("AUC")
    ax.set_title("图7 · 各特征的检测能力对比")
    ax.legend()
    for b, a in zip(bars, aucs):
        ax.text(a + 0.01, b.get_y() + b.get_height() / 2, f"{a:.3f}", va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig7_feature_auc.png"), dpi=150)
    plt.close()
    print("  已保存 fig7_feature_auc.png")


def main():
    print("=" * 90)
    print("实验 02：分层分析（补救 E2 发现的双峰问题）")
    print("=" * 90)

    neg_by_lang, pos_ascii = e5_stratified()
    e6_results = e6_alternative_features()
    e7_combined()

    print("\n" + "=" * 90)
    print("生成图表")
    print("=" * 90)
    make_figures(neg_by_lang, e6_results)

    print("\n实验完成")


if __name__ == "__main__":
    main()
