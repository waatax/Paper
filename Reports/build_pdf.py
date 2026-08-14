"""
Paperluz — 報告 PDF 產製器

用途
    把 Reports/ 下的報告 HTML 轉為 A4 PDF。PDF 是對外交付與存檔的正式格式，
    每期與 .md / .html 同步產出（規格書第一部 1.2、第十一部 11.3）。

設計原則
    版面由報告 HTML 自身的 @media print 區塊決定，本腳本不注入任何樣式。
    這樣「螢幕上看到的」與「PDF 印出來的」永遠出自同一份原始碼，
    不會出現兩份各自演化、內容對不上的情況。

用法
    python build_pdf.py                          轉換最新一期
    python build_pdf.py 2026-W31_paperluz_weekly_002
    python build_pdf.py --all                    重建全部期別
"""

import os
import sys
import glob
import shutil
import subprocess

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Chromium 系瀏覽器的無頭列印是唯一能正確處理內嵌 SVG + 中文字型的免費路徑。
# wkhtmltopdf 對 SVG 與 CSS Grid 支援不完整，WeasyPrint 不支援 <svg> 內的 text 對齊，
# 兩者都會讓圖表變形，因此不列為備援。
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
    raise FileNotFoundError(
        "找不到 Edge 或 Chrome。請安裝其一，或將路徑加入 BROWSER_CANDIDATES。"
    )


def html_to_pdf(html_path: str, browser: str) -> str:
    pdf_path = os.path.splitext(html_path)[0] + ".pdf"
    # file:// URL 讓無頭瀏覽器正確解析中文路徑
    url = "file:///" + html_path.replace("\\", "/")
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=5000",   # 等版面與字型穩定後再擷取
        "--no-pdf-header-footer",       # 頁首頁尾由報告 HTML 自行控制
        f"--print-to-pdf={pdf_path}",
        url,
    ]
    # Windows 預設 cp950 無法解析瀏覽器輸出的 UTF-8 訊息，需顯式指定
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=180,
    )

    if not os.path.exists(pdf_path):
        raise RuntimeError(
            f"PDF 產製失敗：{os.path.basename(html_path)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return pdf_path


def resolve_targets(argv) -> list:
    all_html = sorted(glob.glob(os.path.join(REPORTS_DIR, "PaperLuz-*.html")))
    if not all_html:
        raise FileNotFoundError(f"{REPORTS_DIR} 下找不到報告 HTML。")

    if "--all" in argv:
        return all_html
    if len(argv) > 1:
        slug = argv[1].removesuffix(".html")
        target = os.path.join(REPORTS_DIR, slug + ".html")
        if not os.path.exists(target):
            raise FileNotFoundError(f"找不到 {target}")
        return [target]
    return [all_html[-1]]   # 檔名以 ISO 週開頭，字典序即時間序


def main() -> int:
    browser = find_browser()
    print(f"使用瀏覽器：{browser}\n")

    failures = []
    for html_path in resolve_targets(sys.argv):
        name = os.path.basename(html_path)
        try:
            pdf_path = html_to_pdf(html_path, browser)
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"  OK   {name}  ->  {os.path.basename(pdf_path)}  ({size_kb:,.0f} KB)")
        except Exception as exc:
            print(f"  FAIL {name}\n       {exc}")
            failures.append(name)

    if failures:
        print(f"\n{len(failures)} 份失敗。PDF 是對外交付格式，失敗即視為該期未完成發布。")
        return 1
    print("\n完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
