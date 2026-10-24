"""
exp03_multi_tokenizer.py —— 多 tokenizer 交叉验证
=================================================
E5 发现「token 膨胀在中文场景失效」，但只用了 cl100k_base。
本实验用 4 个 tokenizer 验证结论是否稳健。

关键问题：
    如果换 tokenizer 后绝对数值变化很大，说明「token 膨胀」这个
    特征本身依赖于 tokenizer 的选择 —— 这进一步削弱它作为
    "通用检测信号" 的地位。
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

import tiktoken
from corpus import get_corpus
from carriers import get_carriers

CORPUS = get_corpus()
CARRIERS = get_carriers()

TOKENIZERS = ["cl100k_base", "o200k_base", "p50k_base", "r50k_base"]
_ENCS = {}


def enc(name):
    if name not in _ENCS:
        _ENCS[name] = tiktoken.get_encoding(name)
    return _ENCS[name]


def tpc(text, tok):
    if not text:
        return 0.0
    return len(enc(tok).encode(text)) / len(text)


def script_of(text):
    cjk = sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)
    lat = sum(1 for c in text if "a" <= c.lower() <= "z")
    if cjk > lat * 2:
        return "zh"
    if lat > cjk * 2:
        return "en"
    return "mixed"


def auc(pos_vals, neg_vals):
    """AUC（越大越可疑）。"""
    sorted_neg = np.sort(neg_vals)
    a = 0.0
    for p in pos_vals:
        a += (sorted_neg < p).sum() + 0.5 * (sorted_neg == p).sum()
    return a / (len(pos_vals) * len(neg_vals))


def main():
    print("=" * 95)
    print("实验 03：多 tokenizer 交叉验证")
    print("=" * 95)

    # 正样本（排除明文对照）
    pos_texts = [t for cid, _, _, t in CARRIERS if cid != "C01"]
    # 负样本按语言分组
    neg_by_lang = defaultdict(list)
    for cat, text in CORPUS:
        neg_by_lang[script_of(text)].append(text)

    # ========== E8: 中文句子的 tokenizer 差异 ==========
    print("\n" + "=" * 95)
    print("E8: 同一段中文，不同 tokenizer 的 token 数差异")
    print("=" * 95)

    sample_zh = "本文介绍了一种基于马尔可夫链的序列预测方法，用于分析智能体工具调用序列的结构可预测性。"
    sample_en = "This paper introduces a Markov chain based sequence prediction method."

    print(f"\n中文样本（{len(sample_zh)} 字符）：")
    zh_counts = {}
    for tok in TOKENIZERS:
        n = len(enc(tok).encode(sample_zh))
        zh_counts[tok] = n
        print(f"  {tok:15s} {n:3d} tokens  ({n/len(sample_zh):.3f} t/char)")

    base = zh_counts["cl100k_base"]
    print(f"\n  相对 cl100k_base：")
    for tok, n in zh_counts.items():
        print(f"    {tok:15s} {n/base:>5.2f}x")

    print(f"\n英文样本（{len(sample_en)} 字符）：")
    for tok in TOKENIZERS:
        n = len(enc(tok).encode(sample_en))
        print(f"  {tok:15s} {n:3d} tokens  ({n/len(sample_en):.3f} t/char)")

    # ========== E9: 分语言 AUC 跨 tokenizer ==========
    print("\n" + "=" * 95)
    print("E9: 分语言 AUC —— 跨 4 个 tokenizer")
    print("=" * 95)

    results = {}
    for tok in TOKENIZERS:
        pos_vals = np.array([tpc(t, tok) for t in pos_texts])
        row = {}
        for lang, texts in neg_by_lang.items():
            neg_vals = np.array([tpc(t, tok) for t in texts])
            if len(neg_vals) < 5:
                continue
            a = auc(pos_vals, neg_vals)
            row[lang] = round(float(a), 4)
        results[tok] = row

    print(f"\n{'tokenizer':<16} {'中文 AUC':>12} {'英文 AUC':>12} {'混排 AUC':>12}")
    print("-" * 58)
    for tok in TOKENIZERS:
        r = results[tok]
        print(f"{tok:<16} {r.get('zh', 0):>12.4f} "
              f"{r.get('en', 0):>12.4f} {r.get('mixed', 0):>12.4f}")

    # 检查结论是否稳健
    print(f"\n--- 稳健性检查 ---")
    zh_aucs = [results[t].get("zh", 0) for t in TOKENIZERS]
    en_aucs = [results[t].get("en", 0) for t in TOKENIZERS]
    print(f"中文 AUC 范围: {min(zh_aucs):.4f} ~ {max(zh_aucs):.4f}  "
          f"(全部 < 0.5: {all(a < 0.5 for a in zh_aucs)})")
    print(f"英文 AUC 范围: {min(en_aucs):.4f} ~ {max(en_aucs):.4f}  "
          f"(全部 > 0.7: {all(a > 0.7 for a in en_aucs)})")

    if all(a < 0.5 for a in zh_aucs) and all(a > 0.7 for a in en_aucs):
        print(f"\n[结论稳健] 换任何 tokenizer，'中文失效 / 英文有效' 的模式都不变。")
    else:
        print(f"\n[结论不稳健] 需要重新审视。")

    # ========== E10: 正常文本基线跨 tokenizer ==========
    print("\n" + "=" * 95)
    print("E10: 正常文本的 token/char 基线 —— 跨 tokenizer")
    print("=" * 95)

    print(f"\n{'tokenizer':<16} {'中文均值':>10} {'中文P95':>10} {'英文均值':>10} {'英文P95':>10}")
    print("-" * 60)
    baseline = {}
    for tok in TOKENIZERS:
        zh_vals = np.array([tpc(t, tok) for t in neg_by_lang["zh"]])
        en_vals = np.array([tpc(t, tok) for t in neg_by_lang["en"]])
        baseline[tok] = {
            "zh_mean": round(float(zh_vals.mean()), 3),
            "zh_p95": round(float(np.percentile(zh_vals, 95)), 3),
            "en_mean": round(float(en_vals.mean()), 3),
            "en_p95": round(float(np.percentile(en_vals, 95)), 3),
        }
        print(f"{tok:<16} {zh_vals.mean():>10.3f} {np.percentile(zh_vals,95):>10.3f} "
              f"{en_vals.mean():>10.3f} {np.percentile(en_vals,95):>10.3f}")

    # ========== E11: 载体的 token/char 跨 tokenizer ==========
    print("\n" + "=" * 95)
    print("E11: 载体 token/char —— 跨 tokenizer（检验膨胀率是否稳定）")
    print("=" * 95)

    print(f"\n{'载体':<20} " + " ".join(f"{t[:8]:>9}" for t in TOKENIZERS))
    print("-" * 60)
    carrier_vals = {}
    for cid, name, desc, text in CARRIERS:
        vals = [tpc(text, tok) for tok in TOKENIZERS]
        carrier_vals[name] = vals
        print(f"{name:<20} " + " ".join(f"{v:>9.3f}" for v in vals))

    # 计算每个载体的跨 tokenizer 变异系数
    print(f"\n--- 载体膨胀率的跨 tokenizer 稳定性 ---")
    cv_list = []
    for name, vals in carrier_vals.items():
        arr = np.array(vals)
        cv = arr.std() / arr.mean() if arr.mean() else 0
        cv_list.append((name, cv))
    cv_list.sort(key=lambda x: -x[1])
    print(f"{'载体':<20} {'变异系数':>10}")
    for name, cv in cv_list[:8]:
        print(f"{name:<20} {cv:>10.3f}")
    print(f"\n平均变异系数: {np.mean([c for _, c in cv_list]):.3f}")
    print("（变异系数越大，说明该载体的'膨胀率'越依赖 tokenizer 选择）")

    # 保存
    out = {
        "e8_zh_sample": zh_counts,
        "e9_auc_by_tokenizer": results,
        "e10_baseline": baseline,
        "e11_carrier_tpc": carrier_vals,
        "e11_cv": {n: round(c, 4) for n, c in cv_list},
    }
    with open(os.path.join(OUT, "exp03_multi_tokenizer.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ========== 出图 ==========
    print("\n" + "=" * 95)
    print("生成图表")
    print("=" * 95)

    # 图8：分语言 AUC 跨 tokenizer
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(TOKENIZERS))
    w = 0.25
    for i, (lang, color) in enumerate([("zh", "#e74c3c"), ("en", "#3498db"), ("mixed", "#2ecc71")]):
        vals = [results[t].get(lang, 0) for t in TOKENIZERS]
        ax.bar(x + (i - 1) * w, vals, w, label=lang, color=color)
    ax.axhline(0.5, color="black", linestyle="--", linewidth=1, label="随机 (0.5)")
    ax.set_xticks(x)
    ax.set_xticklabels(TOKENIZERS)
    ax.set_ylabel("AUC")
    ax.set_title("图8 · token 膨胀的判别能力 —— 跨 4 个 tokenizer")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig8_multi_tokenizer_auc.png"), dpi=150)
    plt.close()
    print("  已保存 fig8_multi_tokenizer_auc.png")

    # 图9：载体 t/char 跨 tokenizer
    fig, ax = plt.subplots(figsize=(12, 6))
    names = list(carrier_vals.keys())
    y = np.arange(len(names))
    for i, tok in enumerate(TOKENIZERS):
        vals = [carrier_vals[n][i] for n in names]
        ax.scatter(vals, y, label=tok, alpha=0.7, s=40)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("token / char")
    ax.set_title("图9 · 17 种载体的 token/char —— 在不同 tokenizer 下的分布")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig9_carrier_multi_tokenizer.png"), dpi=150)
    plt.close()
    print("  已保存 fig9_carrier_multi_tokenizer.png")

    print(f"\n实验完成，结果保存到 {OUT}")


if __name__ == "__main__":
    main()
