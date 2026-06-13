# -*- coding: utf-8 -*-
"""
03_build_corpus.py

把 01/02 步的结果整理成最终语料:
1. 摘要语料: 所有论文(无论是否OA)的 title+abstract 整理成 abstracts_corpus.jsonl
2. 全文语料: 02步成功提取的全文txt,汇总统计并生成索引文件 fulltext_index.jsonl

同时输出整体统计报告,方便你了解语料规模(篇数、字数等),
为下一步"构造QA指令数据集"做准备。

用法(Colab):
    !python 03_build_corpus.py
"""

import json
import os

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed")
FULLTEXT_DIR = os.path.join(RAW_DIR, "fulltext_txt")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def build_abstracts_corpus():
    """汇总所有期刊的摘要为一个jsonl文件"""
    metadata_files = [f for f in os.listdir(RAW_DIR) if f.startswith("metadata_") and f.endswith(".jsonl")]

    output_path = os.path.join(PROCESSED_DIR, "abstracts_corpus.jsonl")
    total = 0
    journal_counts = {}

    with open(output_path, "w", encoding="utf-8") as out_f:
        for meta_file in metadata_files:
            journal_name = meta_file[len("metadata_"):-len(".jsonl")]
            path = os.path.join(RAW_DIR, meta_file)

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    out_record = {
                        "journal": record["journal"],
                        "year": record["year"],
                        "title": record["title"],
                        "abstract": record["abstract"],
                        "doi": record["doi"],
                        "concepts": record.get("concepts", []),
                    }
                    out_f.write(json.dumps(out_record, ensure_ascii=False) + "\n")
                    total += 1
                    journal_counts[journal_name] = journal_counts.get(journal_name, 0) + 1

    print(f"[摘要语料] 共 {total} 篇,已保存到 {output_path}")
    for j, c in journal_counts.items():
        print(f"    {j}: {c}")

    return total


def build_fulltext_index():
    """汇总全文txt文件信息,生成索引"""
    if not os.path.exists(FULLTEXT_DIR):
        print("[全文语料] 未找到全文目录,跳过(可能02步未运行或没有OA全文)")
        return 0

    txt_files = [f for f in os.listdir(FULLTEXT_DIR) if f.endswith(".txt")]
    output_path = os.path.join(PROCESSED_DIR, "fulltext_index.jsonl")

    total_chars = 0
    journal_counts = {}

    with open(output_path, "w", encoding="utf-8") as out_f:
        for fname in txt_files:
            fpath = os.path.join(FULLTEXT_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析文件名得到期刊名(格式: <journal>_<doi_safe>.txt)
            journal_name = fname.split("_")[0]
            journal_counts[journal_name] = journal_counts.get(journal_name, 0) + 1
            total_chars += len(content)

            record = {
                "filename": fname,
                "path": fpath,
                "char_count": len(content),
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n[全文语料] 共 {len(txt_files)} 篇,总字符数约 {total_chars:,}")
    for j, c in journal_counts.items():
        print(f"    {j}: {c}")
    print(f"  索引已保存到 {output_path}")

    return len(txt_files)


def main():
    print("========== 整理语料 ==========\n")
    abstract_count = build_abstracts_corpus()
    fulltext_count = build_fulltext_index()

    print("\n========== 总览 ==========")
    print(f"  摘要总数: {abstract_count}")
    print(f"  全文总数: {fulltext_count}")
    print(f"  摘要语料文件: {os.path.join(PROCESSED_DIR, 'abstracts_corpus.jsonl')}")
    print(f"  全文索引文件: {os.path.join(PROCESSED_DIR, 'fulltext_index.jsonl')}")
    print("\n下一步: 用这两份数据通过LLM API生成QA指令数据集(脚本04)")


if __name__ == "__main__":
    main()
