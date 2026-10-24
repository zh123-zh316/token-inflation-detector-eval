"""
detectors.py —— 检测器集合
=========================
7 种提示词注入检测器，从朴素到组合。

关键设计：
    检测器不只看 token 膨胀，而是多种特征，
    这样才能公平比较「token 膨胀」到底值不值。

用法：
    python detectors.py     # 跑检测器对比
"""
import os
import re
import sys
import unicodedata

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# 基础特征
# ============================================================

TAG_BASE = 0xE0000
ZW_CHARS = "\u200b\u200c\u200d\u2060\ufeff\u00ad"
BIDI_CHARS = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"

HOMOGLYPH_KNOWN_REV = {
    "\u0251": "a", "\u0441": "c", "\u0435": "e", "\u0456": "i",
    "\u0458": "j", "\u03bf": "o", "\u0440": "p", "\u0455": "s",
    "\u0445": "x", "\u0443": "y",
    "\u0410": "A", "\u0412": "B", "\u0421": "C", "\u0415": "E",
    "\u041d": "H", "\u0406": "I", "\u041a": "K", "\u041c": "M",
    "\u041e": "O", "\u0420": "P", "\u0405": "S", "\u0422": "T",
    "\u0425": "X", "\u0423": "Y",
}

ATTACK_PAT = re.compile(
    r"(ignore (all )?(previous|prior|above)|disregard|forget (all )?"
    r"|only output|do not (summarize|tell|mention)"
    r"|忽略(之前|先前|上面|前文|所有|上述)|只输出|不要(总结|告诉|提及))",
    re.I,
)

SEND_PAT = re.compile(r"(send|forward|exfiltrat|upload|post|transmit)", re.I)


def has_tag_block(text):
    return bool(re.search(r"[\U000E0020-\U000E007E]", text))


def has_vs(text):
    return any(0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF for c in text)


def zw_ratio(text):
    if not text:
        return 0.0
    return sum(1 for c in text if c in ZW_CHARS) / len(text)


def bidi_count(text):
    return sum(1 for c in text if c in BIDI_CHARS)


def script_mixing(text):
    """拉丁 + 西里尔/希腊混排 —— 同形字的确定性指纹。"""
    lat = sum(1 for c in text if "a" <= c.lower() <= "z")
    cyr = sum(1 for c in text if 0x0400 <= ord(c) <= 0x04FF)
    grk = sum(1 for c in text if 0x0370 <= ord(c) <= 0x03FF)
    return lat > 0 and (cyr > 0 or grk > 0), (lat, cyr, grk)


def fold_homoglyph(text):
    return "".join(HOMOGLYPH_KNOWN_REV.get(c, c) for c in text)


def strip_zw(text):
    return "".join(c for c in text if c not in ZW_CHARS)


def decode_tag(text):
    out = []
    for c in text:
        o = ord(c)
        if TAG_BASE + 0x20 <= o <= TAG_BASE + 0x7E:
            out.append(chr(o - TAG_BASE))
        else:
            out.append(c)
    return "".join(out)


def normalize(text, mode="space"):
    """双路归一化。"""
    s = decode_tag(text)
    s = fold_homoglyph(s)
    if mode == "space":
        s = re.sub(f"[{re.escape(ZW_CHARS)}]", " ", s)
    else:
        s = strip_zw(s)
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip()


# ============================================================
# token 计数
# ============================================================

_enc = None


def count_tokens(text):
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
    return len(_enc.encode(text))


def token_per_char(text):
    if not text:
        return 0.0
    return count_tokens(text) / len(text)


# ============================================================
# 检测器
# ============================================================

def detect_d1_keyword(text):
    """D1：朴素关键词（send/forward/ignore 等）。"""
    return bool(SEND_PAT.search(text) or ATTACK_PAT.search(text))


def detect_d2_tagblock(text):
    """D2：Tag 块存在性。"""
    return has_tag_block(text)


def detect_d3_zw_density(text, th=0.02):
    """D3：零宽密度阈值。"""
    return zw_ratio(text) > th


def detect_d4_token_inflation(text, th=0.85):
    """D4：token/char 比值超过阈值。

    正常文本（中英混排）约 0.2-0.7；混淆载荷可能 > 0.9。
    注意：这是密度指标，与文本长度无关。
    """
    return token_per_char(text) > th


def detect_d5_structural(text, th=0.85):
    """D5：字符块 + 膨胀组合。"""
    if has_tag_block(text):
        return True
    if has_vs(text):
        return True
    if zw_ratio(text) > 0.02:
        return True
    if bidi_count(text) > 0:
        return True
    return token_per_char(text) > th


def detect_d6_hardened(text):
    """D6：双路归一化后再关键词匹配。"""
    for mode in ("space", "drop"):
        v = normalize(text, mode)
        if SEND_PAT.search(v) or ATTACK_PAT.search(v):
            return True
    return False


def detect_d7_full(text, th=0.85):
    """D7：全组合。"""
    return detect_d5_structural(text, th) or detect_d6_hardened(text)


DETECTORS = {
    "D1_keyword": ("朴素关键词", detect_d1_keyword),
    "D2_tagblock": ("Tag块存在性", detect_d2_tagblock),
    "D3_zw_density": ("零宽密度", detect_d3_zw_density),
    "D4_token_inflate": ("token膨胀", detect_d4_token_inflation),
    "D5_structural": ("结构异常组合", detect_d5_structural),
    "D6_hardened": ("归一化加固", detect_d6_hardened),
    "D7_full": ("全组合", detect_d7_full),
}


def score_all(text):
    """返回每个检测器的判定结果 + 关键特征值。"""
    tpc = token_per_char(text)
    return {
        "tokens": count_tokens(text),
        "chars": len(text),
        "token_per_char": tpc,
        "zw_ratio": zw_ratio(text),
        "has_tag": has_tag_block(text),
        "has_vs": has_vs(text),
        "bidi": bidi_count(text),
        "script_mix": script_mixing(text)[0],
        "verdicts": {k: bool(fn(text)) for k, (_, fn) in DETECTORS.items()},
    }


if __name__ == "__main__":
    from carriers import get_carriers

    carriers = get_carriers()
    print("=" * 110)
    print(f"{'编号':<5} {'载体':<20} {'t/char':>7} {'zw%':>6} {'tag':>4} {'vs':>4} "
          f"{'D1':>4} {'D2':>4} {'D3':>4} {'D4':>4} {'D5':>4} {'D6':>4} {'D7':>4}")
    print("-" * 110)
    for cid, name, desc, text in carriers:
        s = score_all(text)
        v = s["verdicts"]
        mark = lambda b: "✓" if b else "·"
        print(f"{cid:<5} {name:<20} {s['token_per_char']:>7.3f} "
              f"{s['zw_ratio']*100:>5.1f}% "
              f"{mark(s['has_tag']):>4} {mark(s['has_vs']):>4} "
              f"{mark(v['D1_keyword']):>4} {mark(v['D2_tagblock']):>4} "
              f"{mark(v['D3_zw_density']):>4} {mark(v['D4_token_inflate']):>4} "
              f"{mark(v['D5_structural']):>4} {mark(v['D6_hardened']):>4} "
              f"{mark(v['D7_full']):>4}")
    print("=" * 110)
