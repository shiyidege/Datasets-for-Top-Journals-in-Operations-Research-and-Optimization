# -*- coding: utf-8 -*-
"""
02_download_oa_fulltext.py

从 01 步生成的元数据中,筛选出 is_oa=True 的论文,下载其OA PDF全文,
并用 PyMuPDF 提取正文文本,保存为 txt。

非OA(付费墙)的论文不下载全文,只保留摘要(已在01步保存)。

输出: data/raw/fulltext_txt/<journal>_<doi安全化>.txt

用法(Colab):
    !pip install pymupdf -q
    !python 02_download_oa_fulltext.py
"""

import json
import os
import re
import time
import requests

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("请先运行: pip install pymupdf")

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
FULLTEXT_DIR = os.path.join(RAW_DIR, "fulltext_txt")
os.makedirs(FULLTEXT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 单篇下载超时/最大文件大小限制(MB),避免遇到异常大文件
MAX_PDF_MB = 30


def safe_filename(text: str) -> str:
    """把doi等字符串转成安全的文件名"""
    text = text or "unknown"
    text = re.sub(r"https?://(doi\.org/|dx\.doi\.org/)?", "", text)
    text = re.sub(r"[^a-zA-Z0-9_.-]", "_", text)
    return text[:120]


def download_pdf(url: str, dest_path: str) -> bool:
    """下载PDF到本地,成功返回True"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            # 有些oa_url指向的是落地页而不是直接PDF,跳过
            return False

        size = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                size += len(chunk)
                if size > MAX_PDF_MB * 1024 * 1024:
                    f.close()
                    os.remove(dest_path)
                    return False
                f.write(chunk)
        return True
    except Exception:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def pdf_to_text(pdf_path: str) -> str:
    """用PyMuPDF提取PDF全文文本"""
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        print(f"    [解析失败] {pdf_path}: {e}")
        return ""


def clean_text(text: str) -> str:
    """简单清洗: 合并多余空行/空格"""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    metadata_files = [f for f in os.listdir(RAW_DIR) if f.startswith("metadata_") and f.endswith(".jsonl")]
    if not metadata_files:
        print("未找到元数据文件,请先运行 01_fetch_metadata.py")
        return

    total_oa = 0
    total_downloaded = 0
    total_extracted = 0

    for meta_file in metadata_files:
        journal_name = meta_file[len("metadata_"):-len(".jsonl")]
        path = os.path.join(RAW_DIR, meta_file)

        with open(path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f]

        oa_records = [r for r in records if r.get("is_oa") and r.get("oa_pdf_url")]
        print(f"\n[{journal_name}] 共 {len(records)} 篇,其中OA可下载 {len(oa_records)} 篇")
        total_oa += len(oa_records)

        for i, r in enumerate(oa_records):
            doi_safe = safe_filename(r.get("doi", f"{journal_name}_{i}"))
            txt_path = os.path.join(FULLTEXT_DIR, f"{journal_name}_{doi_safe}.txt")

            if os.path.exists(txt_path):
                continue  # 已处理过

            pdf_tmp_path = os.path.join(FULLTEXT_DIR, f"_tmp_{journal_name}_{doi_safe}.pdf")

            ok = download_pdf(r["oa_pdf_url"], pdf_tmp_path)
            if not ok:
                continue
            total_downloaded += 1

            text = pdf_to_text(pdf_tmp_path)
            os.remove(pdf_tmp_path)

            if len(text) < 500:  # 提取内容太短,可能是失败的解析
                continue

            text = clean_text(text)

            # 在文本开头写入元信息,方便后续溯源
            header = (
                f"TITLE: {r.get('title')}\n"
                f"JOURNAL: {journal_name}\n"
                f"YEAR: {r.get('year')}\n"
                f"DOI: {r.get('doi')}\n"
                f"---\n\n"
            )

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(header + text)

            total_extracted += 1

            if (i + 1) % 20 == 0:
                print(f"  ... 已处理 {i+1}/{len(oa_records)}")

            time.sleep(0.3)  # 礼貌性限速,避免被对方服务器限流

    print("\n========== 下载汇总 ==========")
    print(f"  OA可下载论文总数: {total_oa}")
    print(f"  成功下载PDF数: {total_downloaded}")
    print(f"  成功提取文本数: {total_extracted}")
    print(f"  全文txt保存在: {FULLTEXT_DIR}")


if __name__ == "__main__":
    main()
