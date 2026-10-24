"""
exp01_token_inflation.py —— 主实验
==================================
实验：Token 膨胀作为提示词注入检测信号的有效性

四个子实验：
    E1 载体谱系的膨胀分布
    E2 正常文本的基线分布（230 条 × 10 类）
    E3 检测器 ROC/AUC 对比（阈值扫描）
    E4 对抗性测试（攻击者规避策略）

输出：
    results/exp01_*.json   原始数据
    results/*.png          图表
    results/summary.md     结论摘要
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

# 中文字体
for f in ["Microsoft YaHei", "SimHei", "SimSun", "DengXian"]:
    try:
        matplotlib.rcParams["font.sans-serif"] = [f]
        matplotlib.rcParams["axes.unicode_minus"] = False
        break
    except Exception:
        continue

from corpus import get_corpus
from carriers import get_carriers, PAYLOAD
from detectors import (
    count_tokens, token_per_char, score_all, DETECTORS,
    detect_d4_token_inflation,
)

CARRIERS = get_carriers()
CORPUS = get_corpus()


# ============================================================
# E1: 载体谱系
# ============================================================

def e1_carrier_spectrum():
    print("\n" + "=" * 90)
    print("E1: 载体谱系的膨胀分布")
    print("=" * 90)

    base_tokens = count_tokens(PAYLOAD)
    rows = []
    for cid, name, desc, text in CARRIERS:
        t = count_tokens(text)
        c = len(text)
        s = score_all(text)
        rows.append({
            "id": cid, "name": name, "desc": desc,
            "chars": c, "tokens": t,
            "token_inflation": round(t / base_tokens, 2),
            "token_per_char": round(s["token_per_char"], 4),
            "zw_ratio": round(s["zw_ratio"], 4),
            "has_tag": s["has_tag"],
            "verdicts": s["verdicts"],
        })

    # 按 token/char 排序
    rows.sort(key=lambda r: r["token_per_char"])

    print(f"\n{'编号':<5} {'载体':<20} {'t/char':>8} {'膨胀':>7} {'D4抓到':>7}")
    print("-" * 55)
    for r in rows:
        print(f"{r['id']:<5} {r['name']:<20} {r['token_per_char']:>8.3f} "
              f"{r['token_inflation']:>6.1f}x "
              f"{'✓' if r['verdicts']['D4_token_inflate'] else '·':>7}")

    caught = sum(1 for r in rows if r["verdicts"]["D4_token_inflate"])
    print(f"\nD4 抓到的载体：{caught}/{len(rows)}")
    print(f"漏掉的：{[r['name'] for r in rows if not r['verdicts']['D4_token_inflate']]}")

    with open(os.path.join(OUT, "exp01_e1_carriers.json"), "w", encoding="utf-8") as f:
        json.dump({"base_tokens": base_tokens, "base_chars": len(PAYLOAD),
                   "carriers": rows}, f, ensure_ascii=False, indent=1)
    return rows


# ============================================================
# E2: 正常语料基线
# ============================================================

def e2_normal_baseline():
    print("\n" + "=" * 90)
    print("E2: 正常文本的 token/char 基线分布")
    print("=" * 90)

    by_cat = defaultdict(list)
    all_tpc = []

    for cat, text in CORPUS:
        tpc = token_per_char(text)
        by_cat[cat].append(tpc)
        all_tpc.append(tpc)

    all_tpc = np.array(all_tpc)

    print(f"\n{'类别':<18} {'条数':>5} {'均值':>8} {'中位':>8} {'P95':>8} {'最大':>8}")
    print("-" * 65)
    cat_stats = {}
    for cat in sorted(by_cat, key=lambda c: -np.mean(by_cat[c])):
        arr = np.array(by_cat[cat])
        st = {
            "n": len(arr), "mean": float(arr.mean()), "median": float(np.median(arr)),
            "p95": float(np.percentile(arr, 95)), "max": float(arr.max()),
        }
        cat_stats[cat] = st
        print(f"{cat:<18} {st['n']:>5d} {st['mean']:>8.3f} {st['median']:>8.3f} "
              f"{st['p95']:>8.3f} {st['max']:>8.3f}")

    overall = {
        "n": len(all_tpc), "mean": float(all_tpc.mean()),
        "median": float(np.median(all_tpc)),
        "p90": float(np.percentile(all_tpc, 90)),
        "p95": float(np.percentile(all_tpc, 95)),
        "p99": float(np.percentile(all_tpc, 99)),
        "max": float(all_tpc.max()),
        "min": float(all_tpc.min()),
        "std": float(all_tpc.std()),
    }
    print(f"\n{'总体':<18} {overall['n']:>5d} {overall['mean']:>8.3f} "
          f"{overall['median']:>8.3f} {overall['p95']:>8.3f} {overall['max']:>8.3f}")
    print(f"\n关键分位数：P90={overall['p90']:.3f}  P95={overall['p95']:.3f}  "
          f"P99={overall['p99']:.3f}  Max={overall['max']:.3f}")

    # 找出最高的几条（用于分析误报风险）
    top = sorted(zip(all_tpc, [c for c, _ in CORPUS], [t for _, t in CORPUS]),
                 key=lambda x: -x[0])[:5]
    print(f"\n正常文本中 token/char 最高的 5 条（误报风险点）：")
    for tpc, cat, text in top:
        print(f"  {tpc:.3f}  [{cat}] {text[:50]}")

    with open(os.path.join(OUT, "exp01_e2_baseline.json"), "w", encoding="utf-8") as f:
        json.dump({"overall": overall, "by_category": cat_stats,
                   "all_values": [float(x) for x in all_tpc]},
                  f, ensure_ascii=False, indent=1)
    return overall, cat_stats, all_tpc


# ============================================================
# E3: 检测器 ROC
# ============================================================

def e3_roc(overall, all_tpc):
    print("\n" + "=" * 90)
    print("E3: 检测器 ROC / AUC 对比")
    print("=" * 90)

    # 正样本 = 混淆载荷（排除明文对照和"稀释法"，因为稀释法本质是正常文本包载荷）
    positives = [(cid, name, text) for cid, name, _, text in CARRIERS
                 if cid not in ("C01",)]
    # 负样本 = 正常语料
    negatives = [text for _, text in CORPUS]

    print(f"正样本（攻击载荷）：{len(positives)} 种载体")
    print(f"负样本（正常文本）：{len(negatives)} 条")

    # 对每个检测器计算混淆矩阵（在固定阈值下）
    results = {}
    for dk, (dname, dfn) in DETECTORS.items():
        tp = sum(1 for _, _, t in positives if dfn(t))
        fn = len(positives) - tp
        fp = sum(1 for t in negatives if dfn(t))
        tn = len(negatives) - fp

        tpr = tp / (tp + fn) if (tp + fn) else 0
        fpr = fp / (fp + tn) if (fp + tn) else 0
        precision = tp / (tp + fp) if (tp + fp) else 0

        results[dk] = {
            "name": dname, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "tpr": round(tpr, 4), "fpr": round(fpr, 4),
            "precision": round(precision, 4),
            "missed": [n for _, n, t in positives if not dfn(t)],
        }

    print(f"\n{'检测器':<22} {'检出':>6} {'漏检':>6} {'误报':>6} {'TPR':>7} {'FPR':>7}")
    print("-" * 70)
    for dk, r in sorted(results.items(), key=lambda x: -x[1]["tpr"]):
        print(f"{r['name']:<22} {r['tp']:>3}/{len(positives):<2} "
              f"{r['fn']:>6} {r['fp']:>6} "
              f"{r['tpr']:>6.1%} {r['fpr']:>6.1%}")

    # D4 的阈值扫描（画 ROC）
    print(f"\n--- D4 (token 膨胀) 阈值扫描 ---")
    ths = np.arange(0.15, 3.5, 0.05)
    roc = []
    pos_tpc = np.array([token_per_char(t) for _, _, t in positives])
    neg_tpc = np.array([token_per_char(t) for t in negatives])

    for th in ths:
        tp = int((pos_tpc > th).sum())
        fp = int((neg_tpc > th).sum())
        tpr = tp / len(pos_tpc)
        fpr = fp / len(neg_tpc)
        roc.append({"th": float(th), "tpr": tpr, "fpr": fpr})

    # 计算 AUC
    # 用所有唯一阈值点
    sorted_neg = np.sort(neg_tpc)
    auc = 0.0
    for p in pos_tpc:
        auc += (sorted_neg < p).sum() + 0.5 * (sorted_neg == p).sum()
    auc /= (len(pos_tpc) * len(neg_tpc))

    print(f"D4 AUC = {auc:.4f}")

    # 找最优阈值（Youden's J = TPR - FPR）
    best = max(roc, key=lambda r: r["tpr"] - r["fpr"])
    print(f"最优阈值 = {best['th']:.2f} (TPR={best['tpr']:.1%}, FPR={best['fpr']:.1%})")

    # 找 FPR <= 1% 的最高 TPR
    low_fpr = [r for r in roc if r["fpr"] <= 0.01]
    if low_fpr:
        b = max(low_fpr, key=lambda r: r["tpr"])
        print(f"FPR<=1% 时：阈值={b['th']:.2f}, TPR={b['tpr']:.1%}")

    results["_d4_roc"] = {"auc": round(auc, 4), "curve": roc, "best": best}
    with open(os.path.join(OUT, "exp01_e3_roc.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    return results, roc


# ============================================================
# E4: 对抗性测试
# ============================================================

def e4_adversarial():
    print("\n" + "=" * 90)
    print("E4: 对抗性测试 —— 攻击者能否压低膨胀率绕过")
    print("=" * 90)

    from carriers import sparse_zw, tag_partial, diluted, homoglyph_encode, HOMOGLYPH_UNSEEN

    strategies = []

    # A1: 部分编码（只编码关键词）
    strategies.append(("A1_部分编码", "只把 ignore/only output 映射 Tag",
                       tag_partial(PAYLOAD)))

    # A2: 稀疏零宽（不同密度）
    for every in (2, 4, 8, 16, 32):
        strategies.append((f"A2_稀疏零宽_{every}", f"每 {every} 字符插一个零宽",
                           sparse_zw(PAYLOAD, every)))

    # A3: 稀释法（不同长度）
    for mult in (1, 3, 5, 10):
        pad = ("The quarterly report indicates steady growth across all business units. "
               "Revenue increased by twelve percent year over year. ") * mult
        strategies.append((f"A3_稀释_{mult}x", f"载荷夹在 {mult} 倍长度正常文本中",
                           pad + PAYLOAD + pad))

    # A4: 低膨胀载体
    strategies.append(("A4_表外同形字", "只用表外同形字（低膨胀）",
                       homoglyph_encode(PAYLOAD, HOMOGLYPH_UNSEEN)))

    # A5: 分片（拆成 3 段，各自低膨胀）
    third = len(PAYLOAD) // 3
    parts = [PAYLOAD[i:i + third] for i in range(0, len(PAYLOAD), third)]
    strategies.append(("A5_分片", "载荷拆成 3 段，各段独立",
                       " ... ".join(p for p in parts)))

    print(f"\n{'策略':<18} {'t/char':>8} {'D4检出':>8} {'D5检出':>8} {'D7检出':>8} {'说明'}")
    print("-" * 100)

    rows = []
    for name, desc, text in strategies:
        s = score_all(text)
        v = s["verdicts"]
        rows.append({
            "strategy": name, "desc": desc,
            "token_per_char": round(s["token_per_char"], 4),
            "d4": v["D4_token_inflate"], "d5": v["D5_structural"], "d7": v["D7_full"],
        })
        print(f"{name:<18} {s['token_per_char']:>8.3f} "
              f"{'抓到' if v['D4_token_inflate'] else '绕过':>8} "
              f"{'抓到' if v['D5_structural'] else '绕过':>8} "
              f"{'抓到' if v['D7_full'] else '绕过':>8} {desc}")

    bypassed = sum(1 for r in rows if not r["d4"])
    print(f"\nD4 被绕过：{bypassed}/{len(rows)} 种策略")

    with open(os.path.join(OUT, "exp01_e4_adversarial.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    return rows


# ============================================================
# 出图
# ============================================================

def make_figures(e1_rows, overall, all_tpc, roc, e3_results, e4_rows):
    # 图1：载体膨胀分布
    fig, ax = plt.subplots(figsize=(11, 6))
    names = [r["name"] for r in e1_rows]
    vals = [r["token_per_char"] for r in e1_rows]
    colors = ["#2ecc71" if v > overall["p99"] else "#e74c3c" if v < 0.3 else "#f39c12"
              for v in vals]
    bars = ax.barh(names, vals, color=colors)
    ax.axvline(overall["p99"], color="blue", linestyle="--", linewidth=1.5,
               label=f"正常文本 P99 = {overall['p99']:.3f}")
    ax.axvline(overall["max"], color="purple", linestyle=":", linewidth=1.5,
               label=f"正常文本 Max = {overall['max']:.3f}")
    ax.set_xlabel("token / char 比值")
    ax.set_title("图1 · 17 种载体的 token/char 比值 vs 正常文本基线")
    ax.legend()
    for b, v in zip(bars, vals):
        ax.text(v + 0.02, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig1_carrier_spectrum.png"), dpi=150)
    plt.close()
    print("  已保存 fig1_carrier_spectrum.png")

    # 图2：正常语料分布
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(all_tpc, bins=40, color="#3498db", alpha=0.7, edgecolor="black")
    ax.axvline(overall["p95"], color="orange", linestyle="--", label=f"P95={overall['p95']:.3f}")
    ax.axvline(overall["p99"], color="red", linestyle="--", label=f"P99={overall['p99']:.3f}")
    ax.axvline(overall["max"], color="purple", linestyle=":", label=f"Max={overall['max']:.3f}")
    ax.set_xlabel("token / char 比值")
    ax.set_ylabel("文本数量")
    ax.set_title(f"图2 · 230 条正常文本的 token/char 分布（10 类语料）")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig2_normal_distribution.png"), dpi=150)
    plt.close()
    print("  已保存 fig2_normal_distribution.png")

    # 图3：ROC 曲线
    fig, ax = plt.subplots(figsize=(7, 7))
    fprs = [r["fpr"] for r in roc]
    tprs = [r["tpr"] for r in roc]
    auc = e3_results["_d4_roc"]["auc"]
    ax.plot(fprs, tprs, "b-", linewidth=2, label=f"D4 token膨胀 (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="随机猜测 (AUC=0.5)")
    ax.set_xlabel("误报率 FPR")
    ax.set_ylabel("检出率 TPR")
    ax.set_title("图3 · D4 (token 膨胀检测) 的 ROC 曲线")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig3_roc.png"), dpi=150)
    plt.close()
    print("  已保存 fig3_roc.png")

    # 图4：检测器对比
    fig, ax = plt.subplots(figsize=(10, 5))
    dnames = [r["name"] for k, r in e3_results.items() if not k.startswith("_")]
    dtpr = [r["tpr"] for k, r in e3_results.items() if not k.startswith("_")]
    dfpr = [r["fpr"] for k, r in e3_results.items() if not k.startswith("_")]
    x = np.arange(len(dnames))
    w = 0.35
    ax.bar(x - w / 2, dtpr, w, label="检出率 TPR", color="#2ecc71")
    ax.bar(x + w / 2, dfpr, w, label="误报率 FPR", color="#e74c3c")
    ax.set_xticks(x)
    ax.set_xticklabels(dnames, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("比例")
    ax.set_title("图4 · 7 种检测器的检出率与误报率对比")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig4_detector_comparison.png"), dpi=150)
    plt.close()
    print("  已保存 fig4_detector_comparison.png")

    # 图5：对抗性测试
    fig, ax = plt.subplots(figsize=(10, 5))
    snames = [r["strategy"] for r in e4_rows]
    svals = [r["token_per_char"] for r in e4_rows]
    scols = ["#2ecc71" if r["d4"] else "#e74c3c" for r in e4_rows]
    ax.barh(snames, svals, color=scols)
    ax.axvline(overall["p99"], color="blue", linestyle="--", label=f"P99={overall['p99']:.3f}")
    ax.set_xlabel("token / char 比值")
    ax.set_title("图5 · 对抗性策略的膨胀率（绿=被D4抓到，红=绕过）")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig5_adversarial.png"), dpi=150)
    plt.close()
    print("  已保存 fig5_adversarial.png")


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 90)
    print("实验 01：Token 膨胀作为提示词注入检测信号")
    print("=" * 90)

    e1_rows = e1_carrier_spectrum()
    overall, cat_stats, all_tpc = e2_normal_baseline()
    e3_results, roc = e3_roc(overall, all_tpc)
    e4_rows = e4_adversarial()

    print("\n" + "=" * 90)
    print("生成图表")
    print("=" * 90)
    make_figures(e1_rows, overall, all_tpc, roc, e3_results, e4_rows)

    print("\n" + "=" * 90)
    print("实验完成")
    print("=" * 90)
    print(f"数据与图表已保存到：{OUT}")


if __name__ == "__main__":
    main()
