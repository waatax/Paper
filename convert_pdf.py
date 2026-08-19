#!/usr/bin/env python3
"""
Paperluz Unified Markdown & HTML to A4 PDF Converter Engine v12.0
==================================================================

功能說明：
  1. 自動尋找系統中的 Microsoft Edge 或 Google Chrome 無頭瀏覽器。
  2. 支援傳入任何 .html 或 .md 檔案進行高解析度 A4 PDF 轉檔。
  3. 自動套用 Paperluz 黃金無空白排版樣式與頁面防切割規則。
  4. 支援批次轉換所有 Reports/ 目錄下的週報與特刊。

用法範例：
  python convert_pdf.py                             # 預設轉換最新一期報告
  python convert_pdf.py --all                       # 批次轉換 Reports/ 下所有報告
  python convert_pdf.py Reports/PaperLuz-003_2026-08-14.html
  python convert_pdf.py paperluz.md
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "Reports")
TEMPLATES_DIR = os.path.join(REPORTS_DIR, "templates")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser() -> str:
    for path in BROWSER_CANDIDATES:
        if os.path.exists(path):
            return path
    for name in ("msedge", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("找不到 Edge 或 Chrome 瀏覽器，請確認安裝。")


def convert_html_to_pdf(html_path: str, browser: str, output_pdf_path: str = None) -> str:
    import urllib.request
    if not output_pdf_path:
        output_pdf_path = os.path.splitext(html_path)[0] + ".pdf"

    url = "file:" + urllib.request.pathname2url(os.path.abspath(html_path))
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=5000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf_path}",
        url,
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        stderr_msg = res.stderr
    except subprocess.TimeoutExpired as e:
        # Chromium headless 有時會在產生 PDF 後卡住不結束。若檔案已成功生成則視為成功。
        stderr_msg = f"Browser timed out after {e.timeout}s."

    if not os.path.exists(output_pdf_path):
        raise RuntimeError(f"PDF 產製失敗：{html_path}\nstderr: {stderr_msg}")
    return output_pdf_path


def convert_md_to_html(md_path: str) -> str:
    import markdown
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    body = md.convert(md_text)

    # Wrap in minimal A4 print template if not a full HTML document
    tmpl_html_path = os.path.join(TEMPLATES_DIR, "report_template.html")
    css = ""
    if os.path.exists(tmpl_html_path):
        with open(tmpl_html_path, "r", encoding="utf-8") as f:
            t = f.read()
            m = re.search(r"<style>(.*?)</style>", t, re.DOTALL)
            if m:
                css = m.group(1)

    html_out = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>{os.path.basename(md_path)}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""
    tmp_html_path = os.path.splitext(md_path)[0] + "_preview.html"
    with open(tmp_html_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    return tmp_html_path


def main():
    parser = argparse.ArgumentParser(description="Paperluz A4 PDF 轉檔工具")
    parser.add_argument("file", nargs="?", help="要轉換的 HTML 或 MD 檔案路徑")
    parser.add_argument("--all", action="store_true", help="轉換 Reports/ 下所有週報 HTML")
    args = parser.parse_args()

    browser = find_browser()
    print(f"Paperluz PDF 轉檔引擎啟動 (瀏覽器: {browser})\n")

    if args.all:
        html_files = sorted(glob.glob(os.path.join(REPORTS_DIR, "PaperLuz-*.html")))
        print(f"找到 {len(html_files)} 份報告 HTML，開始批次轉檔...")
        for h in html_files:
            pdf = convert_html_to_pdf(h, browser)
            kb = os.path.getsize(pdf) / 1024
            print(f"  ✓ {os.path.basename(h)} -> {os.path.basename(pdf)} ({kb:,.0f} KB)")
        print("\n全部週報批次 PDF 轉換完成。")
        return 0

    if args.file:
        target = os.path.abspath(args.file)
        if not os.path.exists(target):
            print(f"錯誤：找不到檔案 {target}")
            return 1
        if target.endswith(".md"):
            tmp_html = convert_md_to_html(target)
            pdf = convert_html_to_pdf(tmp_html, browser, os.path.splitext(target)[0] + ".pdf")
            if os.path.exists(tmp_html):
                os.remove(tmp_html)
        else:
            pdf = convert_html_to_pdf(target, browser)
        kb = os.path.getsize(pdf) / 1024
        print(f"  ✓ 完成：{os.path.basename(target)} -> {os.path.basename(pdf)} ({kb:,.0f} KB)")
        return 0

    # Default to latest issue in Reports
    latest_html = sorted(glob.glob(os.path.join(REPORTS_DIR, "PaperLuz-*.html")))[-1]
    pdf = convert_html_to_pdf(latest_html, browser)
    kb = os.path.getsize(pdf) / 1024
    print(f"  ✓ 轉換最新一期：{os.path.basename(latest_html)} -> {os.path.basename(pdf)} ({kb:,.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
