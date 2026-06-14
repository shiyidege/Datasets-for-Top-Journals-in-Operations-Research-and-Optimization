# 运筹学/管理科学领域 LLM 微调项目

基于 15 个国际顶级期刊的论文语料，对 Qwen2.5-1.5B-Instruct 进行 QLoRA 领域微调，使模型掌握运筹学与管理科学领域的专业知识，能够准确回答理论模型、算法设计、优化方法及管理决策等问题。

---

## 项目概览

```
论文语料采集（OpenAlex API）
        ↓
构造 QA 指令微调数据集（DeepSeek API）
        ↓
QLoRA 微调（Qwen2.5-1.5B-Instruct，T4 GPU）
        ↓
评估（困惑度 + LLM-as-Judge）
```

**运行环境**：Google Colab（T4 GPU，16GB 显存）  
**基座模型**：`Qwen/Qwen2.5-1.5B-Instruct`  
**微调方法**：QLoRA 4-bit（LoRA rank=16，可训练参数约 1.18%）

---

## 阶段一：论文语料采集

### 期刊覆盖范围

覆盖 15 个国际顶级运筹学/管理科学期刊（2018 年至今）：

| 期刊 | 简称 | ISSN |
|---|---|---|
| Management Science | MS | 0025-1909 |
| Operations Research | OR | 0030-364X |
| European Journal of Operational Research | EJOR | 0377-2217 |
| Omega | OMEGA | 0305-0483 |
| Manufacturing & Service Operations Management | MSOM | 1523-4614 |
| Production and Operations Management | POM | 1059-1478 |
| International Journal of Production Economics | IJPE | 0925-5273 |
| Journal of Operations Management | JOM | 0272-6963 |
| Transportation Research Part B | TR-B | 0191-2615 |
| Transportation Research Part E | TR-E | 1366-5545 |
| Transportation Science | TS | 0041-1655 |
| Computers & Operations Research | COR | 0305-0548 |
| Annals of Operations Research | AOR | 0254-5330 |
| Naval Research Logistics | NRL | 0894-069X |
| INFORMS Journal on Computing | IJOC | 1091-9856 |

### 运行步骤

```bash
# 1. 解压项目
!unzip -q or_corpus_pipeline.zip
%cd or_corpus_pipeline

# 2. 安装依赖
!pip install requests pymupdf -q

# 3. 采集元数据 + 摘要（15个期刊，2018年至今，每刊最多1000篇）
!python scripts/01_fetch_metadata.py

# 4. 下载开放获取（OA）论文全文并提取文本
!python scripts/02_download_oa_fulltext.py

# 5. 整理成最终语料
!python scripts/03_build_corpus.py
```

### 采集结果

| 来源 | 数量 |
|---|---|
| 摘要语料（abstracts_corpus.jsonl） | **9,873 篇** |
| 全文语料（OA 开放获取） | **1,274 篇** |
| 全文总字符数 | 约 **1.07 亿字符** |

各期刊摘要数量分布：

| 期刊 | 摘要数 | 期刊 | 摘要数 |
|---|---|---|---|
| Management Science | 1,000 | EJOR | 1,000 |
| Operations Research | 1,000 | POM | 1,000 |
| INFORMS Journal Computing | 1,000 | Annals OR | 979 |
| MSOM | 937 | Transportation Science | 615 |
| Naval Research Logistics | 499 | JOM | 383 |
| TR-E | 345 | IJPE | 336 |
| TR-B | 201 | Omega | 186 |

### 输出文件结构

```
data/
├── raw/
│   ├── metadata_<期刊>.jsonl     # 每个期刊的原始元数据
│   └── fulltext_txt/             # OA论文全文（txt格式）
└── processed/
    ├── abstracts_corpus.jsonl    # 汇总摘要语料
    └── fulltext_index.jsonl      # 全文索引
```

---

## 阶段二：构造 QA 指令微调数据集

### 方法说明

使用 DeepSeek API（`deepseek-chat`）将论文摘要和全文节选转换为"理论问题—推理过程—答案"形式的指令微调数据对。

- **摘要 QA**（`04_generate_qa_from_abstracts.py`）：每篇摘要生成 2 条 QA 对，多线程并发（8 workers），支持断点续传
- **全文节选 QA**（`05_generate_qa_from_fulltext.py`）：每篇全文抽取 2 个节选段落（跳过引言和参考文献区域），每个节选生成 2 条深度 QA 对
- **数据合并与划分**（`06_merge_and_split_dataset.py`）：质量过滤 + 去重 + 按源论文分组划分训练/评估集

### QA 数据样例

```json
{
  "instruction": "根据论文，GSCM压力、实践和绩效之间的关系如何？QR技术如何调节这种关系？",
  "input": "",
  "output": "研究表明，市场和出口压力显著影响GSCM实践，而成本压力影响不显著。内部改进实践显著影响GSCM绩效，外部改进实践对经济绩效有负面影响，生态实践则对环境、经济和运营绩效有积极影响。QR技术抑制了内部改进实践对负面经济绩效的正向影响。"
}
```

```json
{
  "instruction": "实验研究的内部效度面临哪些主要威胁？如何应对这些威胁？",
  "input": "",
  "output": "实验研究的内部效度面临的主要威胁包括：缺乏结果性决策和结果、欺骗、需求效应和不公平比较，以及统计效度问题（如每单元格最小样本量、正确估计方差）。应对方法包括：确保实验情境具有真实决策和结果，减少或避免欺骗，控制需求效应（如采用双盲设计），确保比较组间公平，以及遵循统计最佳实践（如进行功效分析、使用适当样本量）。"
}
```

### 数据集规模

| 项目 | 数量 |
|---|---|
| 总 QA 对数 | **2,100 条** |
| 训练集 | **1,890 条**（90%） |
| 评估集 | **210 条**（10%，按源论文分组隔离） |

> 评估集按**源论文**分组划分，确保同一篇论文的 QA 对不同时出现在训练集和评估集中，避免数据泄露。

---

## 阶段三：QLoRA 微调

### 训练配置

| 参数 | 值 |
|---|---|
| 基座模型 | Qwen2.5-1.5B-Instruct |
| 量化方式 | 4-bit NF4（bitsandbytes） |
| 计算精度 | float16（T4 GPU 兼容） |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| 目标模块 | q/k/v/o_proj, gate/up/down_proj |
| 可训练参数 | 18,464,768（占总参数 **1.18%**） |
| Epochs | 3 |
| Batch size | 2（有效 batch = 2×8 = 16） |
| 梯度累积步数 | 8 |
| 学习率 | 2e-4（cosine 衰减） |
| 优化器 | paged_adamw_32bit |
| 最大序列长度 | 1,024 |

### 训练过程

```
训练前显存: 2.21 / 15.64 GB
Total steps: 375  |  Epochs: 3  |  训练时长: 约35分钟

Step    Training Loss
  50      2.356327
 100      1.891810
 150      1.807935
 200      1.742596
 250      1.729910
 300      1.582847
 350      1.565215

训练后显存: 9.12 GB
```

Loss 从 **2.36 → 1.57**，下降约 **33%**，收敛趋势稳定，无过拟合迹象。

---

## 阶段四：评估

### 评估方案

采用两种互补的客观评估指标：

| 指标 | 原理 | 是否消耗 API |
|---|---|---|
| 困惑度（Perplexity） | 衡量模型对领域文本的预测准确性，越低越好 | 否 |
| LLM-as-Judge | DeepSeek 对基座模型与微调模型的回答进行盲测打分 | 是（约0.05元/30条） |

**评估数据**：评估集中的 210 条 QA 对（训练时完全未见过的源论文）

### 评估结果

#### 困惑度（Perplexity）对比

| 模型 | PPL | 降幅 |
|---|---|---|
| 基座模型（Qwen2.5-1.5B-Instruct） | 18.61 | — |
| 微调后模型 | **11.98** | **↓ 35.6%** |

困惑度降低 35.6%，说明微调后模型对运筹学/管理科学领域文本的预测能力显著提升。

#### LLM-as-Judge 对比（30 条评估样本）

| 结果 | 数量 | 占比 |
|---|---|---|
| 微调模型胜出（B wins） | 25 | **83.3%** |
| 基座模型胜出（A wins） | 5 | 16.7% |
| 平局（tie） | 0 | 0.0% |

| 模型 | 平均专业评分（满分100） |
|---|---|
| 基座模型 | 53.8 |
| 微调后模型 | **72.0** |
| 提升幅度 | **+18.2 分** |

评分维度（各 25 分）：专业准确性 · 推理深度 · 完整性 · 清晰度

#### 可视化结果

![评估结果](eval_result.png)

### 结论

两项指标方向一致，互相印证：

- **PPL 降低 35.6%**：模型对领域词汇、专业表达的预测能力大幅提升
- **Judge 胜率 83.3%，评分提升 +18.2 分**：模型在实际问答场景中的专业性、推理深度和表达质量全面优于基座模型
- 训练 Loss 稳定下降且未出现过拟合，微调效果真实可靠

---

## 文件结构

```
or_corpus_pipeline/
├── scripts/
│   ├── 01_fetch_metadata.py          # OpenAlex API 元数据采集
│   ├── 02_download_oa_fulltext.py    # OA 全文下载与文本提取
│   ├── 03_build_corpus.py            # 语料整理与统计
│   ├── 04_generate_qa_from_abstracts.py  # 摘要→QA对生成
│   ├── 05_generate_qa_from_fulltext.py   # 全文节选→QA对生成
│   └── 06_merge_and_split_dataset.py     # 数据合并、过滤、划分
├── data/
│   ├── raw/                          # 原始采集数据
│   └── processed/                   # 处理后数据与QA数据集
├── OR_Finetune_Eval.ipynb            # 微调+评估 Colab Notebook
└── README.md
```

---

## 依赖环境

```bash
# 语料采集
pip install requests pymupdf ddgs trafilatura openai

# 微调与评估
pip install trl peft datasets transformers accelerate bitsandbytes openai pandas matplotlib
```
