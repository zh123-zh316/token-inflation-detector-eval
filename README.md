# token-inflation-detector-eval

**Token 膨胀能检测提示词注入吗？—— 一个被社区高估的信号**

> 复现材料：17 种注入载体 × 230 条正常语料 × 4 个 tokenizer 的完整实验代码与数据。

---

## 一句话结论

**`token/char` 比值是语言指纹，不是攻击指纹。**

- 英文场景：AUC **0.85**（有效）
- 中文场景：AUC **0.29**（比随机还差）
- 换 4 个 tokenizer 全部验证：中文 AUC 全部 < 0.5，英文全部 > 0.82

---

## 为什么做这个

2026 年 10 月，FreeBuf 首页一篇 AI 安全文章提出：

> "token 膨胀是攻击的代价，也是防御的信号……这是一条比关键词匹配更稳的特征。"

该文只给了一句论断，没有：
- 正常文本的基线分布
- 阈值怎么定
- 漏检率 / 误报率
- 跨语言、跨 tokenizer 的检验

本项目把这个论断做成完整实验，并给出它的**失效边界**。

---

## 核心数据

### 分语言 AUC（4 个 tokenizer 全部验证）

| tokenizer | 中文 AUC | 英文 AUC | 混排 AUC |
|---|---|---|---|
| cl100k_base | 0.2931 | 0.8505 | 0.5534 |
| o200k_base | **0.4942** | 0.8489 | 0.7161 |
| p50k_base | 0.2555 | 0.8291 | 0.3197 |
| r50k_base | 0.2555 | 0.8283 | 0.3197 |

**稳健性**：中文全部 < 0.5，英文全部 > 0.82。

### 同一句话，token 数差 3 倍

中文样本（43 字符）：

| tokenizer | tokens | token/char |
|---|---|---|
| o200k_base | 31 | 0.721 |
| cl100k_base | 48 | 1.116 |
| p50k_base | 94 | 2.186 |

英文对照（70 字符）：**4 个 tokenizer 全部 12 tokens。**

### 对抗性测试：12/12 绕过

| 策略 | token/char | 是否绕过 |
|---|---|---|
| 部分编码 | 0.216 | ✅ |
| 稀疏零宽 ×8 | 0.409 | ✅ |
| 稀释法 ×10 | 0.164 | ✅ |
| 分片 | 0.232 | ✅ |

**稀释法的 token/char 随稀释倍数单调下降**——攻击者可以把膨胀率压到任意低。

### 检测器对比

| 检测器 | 检出率 | 误报率 |
|---|---|---|
| 全组合 | 75.0% | 50.4% |
| 归一化加固 | 56.2% | **2.6%** |
| token 膨胀 | 43.8% | **47.4%** |
| 零宽密度 | 25.0% | **0.0%** |
| Tag 块存在性 | 12.5% | **0.0%** |

---

## 目录结构

```
.
├── corpus.py                       # 230 条正常语料（10 类）
├── carriers.py                     # 17 种注入载体实现
├── detectors.py                    # 7 种检测器
├── labkit.py                       # 基础工具箱（Unicode 编解码、归一化、自检）
├── exp01_token_inflation.py        # E1-E4：载体谱系、基线、ROC、对抗性
├── exp02_language_stratified.py    # E5-E7：分层分析、替代特征、组合检测器
├── exp03_multi_tokenizer.py        # E8-E11：多 tokenizer 交叉验证
├── results/                        # 原始数据（JSON）+ 图表（PNG）
└── article.md                      # 文章全文
```

---

## 快速开始

```bash
pip install tiktoken numpy pandas matplotlib

# 1. 基础自检（18 条断言）
python labkit.py selftest

# 2. 载体谱系
python carriers.py

# 3. 检测器对比
python detectors.py

# 4. 主实验
python exp01_token_inflation.py

# 5. 分层分析
python exp02_language_stratified.py

# 6. 多 tokenizer
python exp03_multi_tokenizer.py
```

全部结果输出到 `results/`。

---

## 语料说明

230 条文本，10 类，设计目标是**覆盖"正常但 token/char 比值高"的合法情况**：

| 类别 | 条数 | 平均字符 | 为什么要包含 |
|---|---|---|---|
| zh_tech | 30 | 64 | 中文技术文档 |
| en_tech | 30 | 154 | 英文技术文档 |
| mixed | 30 | 62 | 中英混排 |
| short | 30 | 8 | 短标题（token 密度最高） |
| code | 20 | 97 | 代码片段 |
| json_data | 20 | 90 | 结构化数据 |
| emoji | 20 | 38 | **emoji 多字节** |
| special_symbols | 20 | 43 | 数学/货币符号 |
| multilang | 20 | 50 | 日韩俄阿泰希希伯来 |
| long_form | 10 | 271 | 长段落 |

**emoji 和多语言是关键的压力测试**——它们是正常文本，但 token/char 天然偏高。如果检测器把它们判成攻击，说明阈值定错了。

---

## 局限

1. 语料是自造的，不是真实业务数据（可直接替换 `corpus.py` 重跑）
2. 载体谱系不穷尽
3. 没测真实模型的响应（只测文本层面能否被检出）
4. tokenizer 都是 OpenAI 系列，未覆盖国产模型（但国产模型对中文效率更高，结论方向只会更强）
5. 语言分类用汉字/拉丁字母比例，对边界情况可能误判

---

## 引用

如果这个项目对你有用：

```bibtex
@misc{token_inflation_eval_2026,
  title  = {Token Inflation as a Prompt Injection Detector: An Overestimated Signal},
  year   = {2026},
  note   = {17 carriers, 230 benign texts, 4 tokenizers},
  url    = {https://github.com/<your-username>/token-inflation-detector-eval}
}
```

---

## 声明

- 本项目全部实验在自建环境完成，不涉及任何真实系统
- 载荷中的标记字符串（如 `XZ-7749`）均为无害标识符
- 所有技术内容仅用于授权安全测试、防御研究与教育
- 未授权使用本项目技术攻击他人系统是违法的

## License

MIT
