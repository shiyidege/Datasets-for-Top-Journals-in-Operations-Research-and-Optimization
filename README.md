# 运筹学/管理科学 论文语料采集流程(国外期刊)

## 使用步骤(Colab)

```python
# 1. 上传并解压项目
!unzip -q or_corpus_pipeline.zip
%cd or_corpus_pipeline

# 2. 安装依赖
!pip install requests pymupdf -q

# 3. 修改 scripts/01_fetch_metadata.py 中的 POLITE_EMAIL 为你的邮箱(可选但推荐)

# 4. 采集元数据+摘要(15个国际期刊, 2018年至今, 每刊最多1000篇)
!python scripts/01_fetch_metadata.py

# 5. 下载开放获取(OA)论文全文并提取文本
!python scripts/02_download_oa_fulltext.py

# 6. 整理成最终语料
!python scripts/03_build_corpus.py
```

## 输出结果

- `data/raw/metadata_<期刊>.jsonl`: 每个期刊的原始元数据(标题/摘要/年份/DOI/是否OA等)
- `data/raw/fulltext_txt/<期刊>_<doi>.txt`: 开放获取论文的全文文本
- `data/processed/abstracts_corpus.jsonl`: 汇总后的摘要语料(所有论文,无论是否OA)
- `data/processed/fulltext_index.jsonl`: 全文语料索引

## 关于数据规模的预期

- 摘要语料: 15个期刊 × 最多1000篇 ≈ 数千到上万篇摘要,这部分量级足够大,且全部合法。
- 全文语料: 取决于各期刊的OA比例,EJOR/Omega等期刊近年OA比例提升(很多作者选择付费OA),
  但Management Science/Operations Research等INFORMS期刊OA比例较低,预计全文数量
  会明显少于摘要数量(可能几百到一千多篇)。

## 关于运行时间

01步(元数据采集): 15个期刊,每个期刊最多5次API请求(每次200条),受限速影响,
预计10-20分钟。

02步(全文下载): 取决于OA论文数量,每篇下载+解析约1-3秒,如果OA论文有几百篇,
预计10-30分钟。

## 下一步

跑完后把 `data/processed/abstracts_corpus.jsonl` 和 `data/processed/fulltext_index.jsonl`
的统计结果(脚本会打印篇数汇总)告诉我,我据此设计第4步:
用LLM API把这些摘要/全文转成"理论问题-推理-答案"形式的指令微调数据集(QA pairs),
这是直接影响微调效果的关键一步。
