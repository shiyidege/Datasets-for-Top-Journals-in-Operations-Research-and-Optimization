# -*- coding: utf-8 -*-
"""
01_fetch_metadata.py

用 OpenAlex API 批量拉取指定期刊近年论文的元数据 + 摘要。
OpenAlex 免费、无需API Key、对学术用途友好(建议带上邮箱作为User-Agent的一部分,
这是OpenAlex官方推荐的"polite pool"做法,可以获得更稳定的访问速度)。

输出: data/raw/metadata_<journal>.jsonl
每行一个JSON对象,包含: title, abstract, year, doi, journal, is_oa, oa_pdf_url, concepts

用法(Colab):
    !python 01_fetch_metadata.py
"""

import json
import os
import time
import requests

# ========== 配置 ==========
# 把这里换成你自己的邮箱,OpenAlex会把你放入"polite pool"(更快更稳定)
POLITE_EMAIL = "xiong_zhaoyang@163.com"

# 国际期刊清单: 名称 -> ISSN
JOURNALS = {
    "Management_Science": "0025-1909",
    "Operations_Research": "0030-364X",
    "EJOR": "0377-2217",
    "Omega": "0305-0483",
    "MSOM": "1523-4614",
    "POM": "1059-1478",
    "IJPE": "0925-5273",
    "JOM": "0272-6963",
    "TR_B": "0191-2615",
    "TR_E": "1366-5545",
    "Transportation_Science": "0041-1655",
    "Computers_OR": "0305-0548",
    "Annals_OR": "0254-5330",
    "Naval_Research_Logistics": "0894-069X",
    "INFORMS_Journal_Computing": "1091-9856",
}

# 起始年份(论文发表日期 >= 此年份)
FROM_YEAR = "2018-01-01"

# 每个期刊最多拉取多少篇(防止单期刊数据量过大;OpenAlex单页最多200条)
MAX_PER_JOURNAL = 1000

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://api.openalex.org/works"
HEADERS = {"User-Agent": f"mailto:{POLITE_EMAIL}"}


def reconstruct_abstract(inverted_index: dict) -> str:
    """
    OpenAlex 把摘要存成 'abstract_inverted_index' 格式
    (单词 -> 出现位置列表),需要还原成正常文本。
    """
    if not inverted_index:
        return ""

    position_word = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            position_word[pos] = word

    if not position_word:
        return ""

    max_pos = max(position_word.keys())
    words = [position_word.get(i, "") for i in range(max_pos + 1)]
    return " ".join(words)


def fetch_journal(journal_name: str, issn: str):
    """拉取单个期刊的论文元数据,分页拉取直到达到MAX_PER_JOURNAL或没有更多数据"""
    output_path = os.path.join(OUTPUT_DIR, f"metadata_{journal_name}.jsonl")
    if os.path.exists(output_path):
        print(f"[跳过] {journal_name} 已存在采集结果: {output_path}")
        return

    print(f"\n[采集] {journal_name} (ISSN: {issn}) ...")

    collected = 0
    cursor = "*"  # OpenAlex 游标分页

    with open(output_path, "w", encoding="utf-8") as f:
        while collected < MAX_PER_JOURNAL:
            params = {
                "filter": f"primary_location.source.issn:{issn},from_publication_date:{FROM_YEAR},type:article",
                "per-page": 200,
                "cursor": cursor,
                "select": "id,title,publication_year,doi,abstract_inverted_index,open_access,primary_location,concepts",
            }

            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                print(f"  [错误] HTTP {resp.status_code}: {resp.text[:200]}")
                break

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for work in results:
                abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
                if not abstract:
                    continue  # 没有摘要的论文跳过(对语料质量影响大)

                oa_info = work.get("open_access", {})
                primary_loc = work.get("primary_location") or {}

                record = {
                    "id": work.get("id"),
                    "title": work.get("title"),
                    "abstract": abstract,
                    "year": work.get("publication_year"),
                    "doi": work.get("doi"),
                    "journal": journal_name,
                    "is_oa": oa_info.get("is_oa", False),
                    "oa_pdf_url": oa_info.get("oa_url"),
                    "landing_page_url": primary_loc.get("landing_page_url"),
                    "concepts": [c.get("display_name") for c in (work.get("concepts") or [])[:5]],
                }

                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                collected += 1

                if collected >= MAX_PER_JOURNAL:
                    break

            print(f"  已采集 {collected} 篇...")

            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break

            time.sleep(0.2)  # 礼貌性限速

    print(f"[完成] {journal_name}: 共 {collected} 篇,已保存到 {output_path}")


def main():
    for journal_name, issn in JOURNALS.items():
        try:
            fetch_journal(journal_name, issn)
        except Exception as e:
            print(f"[异常] {journal_name} 采集失败: {e}")

    # 汇总统计
    print("\n========== 采集汇总 ==========")
    total = 0
    for journal_name in JOURNALS:
        path = os.path.join(OUTPUT_DIR, f"metadata_{journal_name}.jsonl")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
            print(f"  {journal_name}: {count} 篇")
            total += count
    print(f"  -------------------------")
    print(f"  总计: {total} 篇")


if __name__ == "__main__":
    main()
