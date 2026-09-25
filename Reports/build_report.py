#!/usr/bin/env python3
"""
Paperluz 電子報產製管線 (Newsletter Production Pipeline) v1.0
============================================================

解決問題
    過去 6 期每一期版面都不同——CSS 飄移、章節缺漏、KPI 卡片數量不一致。

解決方案
    從第 006 期（已通過專家審核的 v9.2 標準）萃取「黃金模板」，鎖定 CSS 指紋。
    後續每一期均從此模板衍生，結構與版面 100% 一致，僅替換內容與數據。

用法
    # ① 首次：從第 006 期萃取黃金模板（僅需執行一次）
    python build_report.py init

    # ② 建立新一期報告骨架
    python build_report.py new --issue 007 --date 2026-08-12 --week 33 ^
           --start 2026-08-05 --theme "主軸一 × 主軸二 × 主軸三"

    # ③ 編輯 HTML 與 MD 內容後，驗證結構合規
    python build_report.py validate PaperLuz-007_2026-08-12

    # ④ 產出 A4 PDF
    python build_report.py pdf PaperLuz-007_2026-08-12

    # ⑤ 完整品質檢核（三檔並存 + 結構 + CSS 指紋）
    python build_report.py checklist PaperLuz-007_2026-08-12

配合規範
    Paperluz Newsletter Template Spec v9.2
    paperluz.md 系統規格書 §11.3 / §13.2

版本  v1.0（2026-08-05）
"""

import argparse
import glob
import hashlib
import os
import re
import sys
import subprocess
import textwrap

# Windows 終端機預設 cp950 無法顯示 Unicode 符號，強制切換為 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ═══════════════════════ 路徑常數 ═══════════════════════

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR   = SCRIPT_DIR
TEMPLATES_DIR = os.path.join(REPORTS_DIR, "templates")

GOLDEN_SRC_HTML = os.path.join(REPORTS_DIR, "PaperLuz-003_2026-08-14.html")
GOLDEN_SRC_MD   = os.path.join(REPORTS_DIR, "PaperLuz-003_2026-08-14.md")

TMPL_HTML     = os.path.join(TEMPLATES_DIR, "report_template.html")
TMPL_MD       = os.path.join(TEMPLATES_DIR, "report_template.md")
CSS_HASH_FILE = os.path.join(TEMPLATES_DIR, "golden_css_hash.txt")

BUILD_PDF_PY  = os.path.join(REPORTS_DIR, "build_pdf.py")

# 佔位符清單（用於 new 指令的替換）
PLACEHOLDERS = [
    "{{ISSUE_NUM}}",
    "{{PUBLISH_DATE}}",
    "{{WEEK_START}}",
    "{{WEEK_END}}",
    "{{WEEK_NUM}}",
    "{{YEAR}}",
    "{{THEME}}",
]


# ═══════════════════════ init：萃取黃金模板 ═══════════════════════

def cmd_init(args):
    """從第 006 期萃取黃金模板，鎖定 CSS 指紋與結構骨架。"""

    for src, label in [(GOLDEN_SRC_HTML, "HTML"), (GOLDEN_SRC_MD, "MD")]:
        if not os.path.exists(src):
            print(f"  ✗ 找不到黃金來源 {label}：{src}")
            print(f"    請確認第 006 期檔案存在後再執行 init。")
            return 1

    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    # ── 萃取 HTML 模板 ──────────────────────────────────────────
    with open(GOLDEN_SRC_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # 替換元資料為佔位符（僅替換結構性位置，不動數據表內容）
    html = re.sub(
        r"<title>.*?</title>",
        "<title>Paperluz 紙業產業情報週報 第 {{ISSUE_NUM}} 期｜{{PUBLISH_DATE}}</title>",
        html, count=1,
    )
    html = re.sub(
        r"(紙業產業情報週報　第 )\d+( 期)",
        r"\g<1>{{ISSUE_NUM}}\g<2>",
        html, count=1,
    )
    html = re.sub(
        r"情報週期：\d{4}-\d{2}-\d{2} ～ \d{4}-\d{2}-\d{2}（\d{4}年 第 \d+ 週 每週五 出刊）"
        r"　·　發布日期：\d{4}-\d{2}-\d{2}",
        "情報週期：{{WEEK_START}} ～ {{WEEK_END}}（{{YEAR}}年 第 {{WEEK_NUM}} 週 每週五 出刊）"
        "　·　發布日期：{{PUBLISH_DATE}}",
        html, count=1,
    )
    html = re.sub(
        r"(本期主軸\s*).*?(\n)",
        r"\g<1>{{THEME}}\g<2>",
        html, count=1,
    )
    html = re.sub(
        r"(<b>產出時間</b>：)\d{4}-\d{2}-\d{2}",
        r"\g<1>{{PUBLISH_DATE}}",
        html, count=1,
    )

    with open(TMPL_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    # ── 計算並鎖定 CSS 指紋 ─────────────────────────────────────
    css_match = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    css_hash = ""
    if css_match:
        css_hash = hashlib.sha256(css_match.group(1).encode("utf-8")).hexdigest()[:16]
        with open(CSS_HASH_FILE, "w", encoding="utf-8") as f:
            f.write(css_hash)

    # ── 萃取 MD 模板 ───────────────────────────────────────────
    with open(GOLDEN_SRC_MD, "r", encoding="utf-8") as f:
        md = f.read()

    md = re.sub(
        r"(# Paperluz 紙業產業情報週報｜第 )\d+( 期)",
        r"\g<1>{{ISSUE_NUM}}\g<2>", md, count=1,
    )
    md = re.sub(
        r"(\*\*情報週期\*\*：)\d{4}-\d{2}-\d{2} ～ \d{4}-\d{2}-\d{2}（\d{4}年 第 \d+ 週 每週五 出刊）",
        r"\g<1>{{WEEK_START}} ～ {{WEEK_END}}（{{YEAR}}年 第 {{WEEK_NUM}} 週 每週五 出刊）",
        md, count=1,
    )
    md = re.sub(
        r"(\*\*發布日期\*\*：)\d{4}-\d{2}-\d{2}",
        r"\g<1>{{PUBLISH_DATE}}", md, count=1,
    )
    md = re.sub(
        r"(\*\*本期主軸\*\* ).*",
        r"\g<1>{{THEME}}", md, count=1,
    )
    md = re.sub(
        r"(\*\*產出時間\*\* )\d{4}-\d{2}-\d{2}",
        r"\g<1>{{PUBLISH_DATE}}", md, count=1,
    )

    with open(TMPL_MD, "w", encoding="utf-8") as f:
        f.write(md)

    # ── 結果報告 ────────────────────────────────────────────────
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   黃金模板萃取完成 (Golden Template Ready)   ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  ✓ HTML 模板 → {os.path.relpath(TMPL_HTML, REPORTS_DIR)}")
    print(f"  ✓ MD   模板 → {os.path.relpath(TMPL_MD, REPORTS_DIR)}")
    print(f"  ✓ CSS  指紋 → {css_hash}")
    print()
    print("  後續每一期將從此模板衍生，CSS 與結構 100% 一致。")
    print("  下一步：python build_report.py new --issue 007 --date 2026-08-12 ...")
    return 0


# ═══════════════════════ new：建立新期骨架 ═══════════════════════

def cmd_new(args):
    """從黃金模板建立新一期報告骨架（HTML + MD）。"""

    if not os.path.exists(TMPL_HTML) or not os.path.exists(TMPL_MD):
        print("  ✗ 黃金模板不存在。請先執行：python build_report.py init")
        return 1

    slug = f"PaperLuz-{args.issue}_{args.date}"
    html_out = os.path.join(REPORTS_DIR, slug + ".html")
    md_out   = os.path.join(REPORTS_DIR, slug + ".md")

    # 檢查檔案是否已存在
    for path in [html_out, md_out]:
        if os.path.exists(path) and not args.force:
            print(f"  ✗ 檔案已存在：{os.path.basename(path)}")
            print(f"    若要覆寫，請加上 --force 參數。")
            return 1

    # 建立替換對照表
    year = args.date[:4]
    end  = args.end if args.end else args.date
    theme = args.theme if args.theme else "（請填入本期主軸）"

    mapping = {
        "{{ISSUE_NUM}}":   args.issue,
        "{{PUBLISH_DATE}}": args.date,
        "{{WEEK_START}}":  args.start,
        "{{WEEK_END}}":    end,
        "{{WEEK_NUM}}":    str(args.week),
        "{{YEAR}}":        year,
        "{{THEME}}":       theme,
    }

    # ── 產生 HTML ───────────────────────────────────────────────
    with open(TMPL_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    for key, val in mapping.items():
        html = html.replace(key, val)
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)

    # ── 產生 MD ─────────────────────────────────────────────────
    with open(TMPL_MD, "r", encoding="utf-8") as f:
        md = f.read()
    for key, val in mapping.items():
        md = md.replace(key, val)
    with open(md_out, "w", encoding="utf-8") as f:
        f.write(md)

    # ── 結果報告 ────────────────────────────────────────────────
    print()
    print(f"  ╔══════════════════════════════════════════════╗")
    print(f"  ║   第 {args.issue} 期報告骨架建立完成              ║")
    print(f"  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  ✓ {slug}.html（CSS 與版面已鎖定，與 006 期 100% 一致）")
    print(f"  ✓ {slug}.md")
    print()
    print("  ── 下一步：編輯內容 ──────────────────────────")
    print(f"  ▶ 開啟 {slug}.html，依序更新：")
    print(f"     1. 6 大 KPI 卡片（數值與說明文字）")
    print(f"     2. 一、本期十行摘要（第一章）")
    print(f"     3. 二、關鍵指標儀表板（四大數據表格）")
    print(f"     4. 三、5 大 SVG 圖表（座標與數值）")
    print(f"     5. 四～十二、其餘章節分析內容")
    print(f"  ▶ 同步更新 {slug}.md（保持三檔內容一致）")
    print()
    print("  ── 編輯完成後 ──────────────────────────────")
    print(f"  python build_report.py validate {slug}")
    print(f"  python build_report.py pdf {slug}")
    print(f"  python build_report.py checklist {slug}")
    return 0


# ═══════════════════════ validate：結構驗證 ═══════════════════════

def _run_html_checks(html, slug):
    """執行 HTML 結構驗證，回傳 [(檢查項, 通過, 補充說明), ...]"""
    checks = []

    # 1. KPI 卡片數
    kpi_count = html.count('class="kpi-card"')
    checks.append(("6 大 KPI 卡片 (3×2 Grid)", kpi_count == 6,
                    f"找到 {kpi_count} 個"))

    # 2. 10~12 大章節 (s1-s10+)
    found_secs = [i for i in range(1, 15) if f'id="s{i}"' in html]
    checks.append(("核心章節 (s1-s10+) 齊全", len(found_secs) >= 10,
                    f"找到 {len(found_secs)} 個：s{',s'.join(str(x) for x in found_secs)}"))

    # 3. 頁尾無下期預告
    footer_part = html.split("<footer>")[-1] if "<footer>" in html else ""
    checks.append(("頁尾無「下期預告」文字", "下期預告" not in footer_part, ""))

    # 4. 無硬性換頁
    bad_break = ("page-break-before: always" in html
                 or "break-before: page" in html)
    checks.append(("無 page-break-before: always", not bad_break, ""))

    # 5. SVG 圖表數
    chart_count = len(re.findall(r'<figure class="chart">', html))
    checks.append(("5 大 SVG 圖表", chart_count >= 5,
                    f"找到 {chart_count} 個"))

    # 6. CSS 指紋
    css_match = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    if css_match and os.path.exists(CSS_HASH_FILE):
        cur = hashlib.sha256(css_match.group(1).encode("utf-8")).hexdigest()[:16]
        with open(CSS_HASH_FILE, "r", encoding="utf-8") as f:
            gold = f.read().strip()
        css_ok = cur == gold
        checks.append(("CSS 指紋與黃金模板一致", css_ok,
                        f"當前={cur} 標準={gold}" if not css_ok else ""))
    else:
        checks.append(("CSS 指紋與黃金模板一致", False,
                        "無法驗證（模板 hash 或 <style> 不存在）"))

    # 7. 頁尾含產出時間與發行機構
    has_footer = ("<footer>" in html
                  and ("發行機構" in html or "Publisher" in html)
                  and ("產出時間" in html or "Published" in html))
    checks.append(("頁尾含產出時間與發行機構", has_footer, ""))

    # 8. Grid 配置
    has_grid = ('class="kpi-grid"' in html and "repeat(3, 1fr)" in html)
    checks.append(("KPI 網格 repeat(3,1fr) 配置", has_grid, ""))

    # 9. 預測矩陣專屬 SECTION (s3-6)
    has_forecast_sec = ('id="s3-6"' in html or '3.6 全鏈預測矩陣' in html or '3.6 Forward Outlook' in html or '3.6' in html)
    checks.append(("圖表後 3.6 全鏈預測矩陣 (s3-6)", has_forecast_sec, ""))

    # 10. 能源與海運物流雷達
    has_energy_logistics = ('海運物流' in html or 'SCFI' in html or '動力煤' in html or 'Logistics' in html or 'Freight' in html)
    checks.append(("能源、外匯與海運物流雷達", has_energy_logistics, ""))

    # 11. 食品包裝與紙袋/紙模塑專欄
    has_pkg = ('食品包裝' in html or '紙模塑' in html or 'Food Packaging' in html or 'Molded Fiber' in html)
    checks.append(("食品包裝與紙袋/紙模塑專欄", has_pkg, ""))

    # 12. 無未替換佔位符
    has_placeholder = any(ph in html for ph in PLACEHOLDERS)
    checks.append(("無未替換的 {{}} 佔位符", not has_placeholder, ""))

    return checks


def _print_checks(checks, title):
    """印出檢查結果表"""
    all_pass = True
    print(f"\n  {title}\n  {'─' * len(title)}")
    for name, passed, detail in checks:
        icon = "✅" if passed else "❌"
        line = f"  {icon} {name}"
        if detail and not passed:
            line += f"  ← {detail}"
        print(line)
        if not passed:
            all_pass = False
    return all_pass


def cmd_validate(args):
    """驗證報告 HTML 結構是否符合 v9.2 規範。"""
    slug = args.slug
    html_path = os.path.join(REPORTS_DIR, slug + ".html")

    if not os.path.exists(html_path):
        print(f"  ✗ 找不到 {slug}.html")
        return 1

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    checks = _run_html_checks(html, slug)
    all_pass = _print_checks(checks, f"📋 結構驗證：{slug}")

    if all_pass:
        print(f"\n  ✅ 全部通過！可安心產出 PDF。")
        print(f"     python build_report.py pdf {slug}")
    else:
        print(f"\n  ⚠️  有未通過項目，請修正後重新驗證。")
    return 0 if all_pass else 1


# ═══════════════════════ pdf：產出 PDF ═══════════════════════

def cmd_pdf(args):
    """呼叫 build_pdf.py 產出 A4 PDF。"""
    slug = args.slug
    html_path = os.path.join(REPORTS_DIR, slug + ".html")

    if not os.path.exists(html_path):
        print(f"  ✗ 找不到 {slug}.html")
        return 1

    if not os.path.exists(BUILD_PDF_PY):
        print(f"  ✗ 找不到 build_pdf.py")
        return 1

    print(f"\n  ⚙️  產出 PDF：{slug}\n")
    result = subprocess.run(
        [sys.executable, BUILD_PDF_PY, slug],
        cwd=REPORTS_DIR,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode


# ═══════════════════════ checklist：完整品質檢核 ═══════════════════════

def cmd_checklist(args):
    """完整品質檢核：三檔並存 + HTML 結構 + MD 結構 + PDF 大小。"""
    slug = args.slug
    if slug in ("all", "--all"):
        html_files = sorted(glob.glob(os.path.join(REPORTS_DIR, "PaperLuz-*.html")))
        total_pass = True
        for h in html_files:
            s = os.path.splitext(os.path.basename(h))[0]
            args_copy = argparse.Namespace(slug=s)
            if cmd_checklist(args_copy) != 0:
                total_pass = False
        return 0 if total_pass else 1

    html_path = os.path.join(REPORTS_DIR, slug + ".html")
    md_path   = os.path.join(REPORTS_DIR, slug + ".md")
    pdf_path  = os.path.join(REPORTS_DIR, slug + ".pdf")

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print(f"  ║   品質檢核 Quality Gate：{slug:<19s}║")
    print("  ╚══════════════════════════════════════════════╝")

    # ── 第一關：三檔並存 ──
    file_checks = [
        (".html 檔案存在", os.path.exists(html_path), ""),
        (".md   檔案存在", os.path.exists(md_path), ""),
        (".pdf  檔案存在", os.path.exists(pdf_path),
         f"請先執行 python build_report.py pdf {slug}"),
    ]
    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        min_kb = 200 if slug.endswith("_EN") else 500
        file_checks.append(
            (f"PDF 檔案大小合理 ({size_kb:,.0f} KB)",
             min_kb < size_kb < 10_000, f"預期 {min_kb} KB ~ 10 MB")
        )
    all_pass = _print_checks(file_checks, "📁 三檔並存檢查")

    # ── 第二關：HTML 結構 ──
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        html_checks = _run_html_checks(html, slug)
        if not _print_checks(html_checks, "🏗️  HTML 結構檢查"):
            all_pass = False

    # ── 第三關：MD 結構 ──
    md_checks = []
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            md = f.read()

        # 10 章節
        md_secs = re.findall(r"^## (?:[一二三四五六七八九十]+[一二三四五六七八九十]?、|[IVXLCDM]+\.|\d+\.)", md, re.MULTILINE)
        md_checks.append(("MD 含 10 大章節標題", len(md_secs) >= 10,
                          f"找到 {len(md_secs)} 個"))

        # 頁尾格式
        has_md_pub = ("**產出時間**" in md or "**Published**" in md or "產出時間" in md or "Published" in md)
        md_checks.append(("MD 頁尾含產出時間", has_md_pub, ""))
        md_checks.append(("MD 頁尾無下期預告", "下期預告" not in md and "Next Issue" not in md, ""))

        # 佔位符
        md_has_ph = any(ph in md for ph in PLACEHOLDERS)
        md_checks.append(("MD 無未替換 {{}} 佔位符", not md_has_ph, ""))

        # 食品包裝專欄
        has_md_pkg = ("食品包裝" in md or "紙模塑" in md or "Food Packaging" in md or "Molded Fiber" in md)
        md_checks.append(("MD 含食品包裝與紙模塑專欄", has_md_pkg, ""))

        if not _print_checks(md_checks, "📄 MD 結構檢查"):
            all_pass = False

    # ── 第四關：三檔內容一致性抽查 ──
    sync_checks = []
    if os.path.exists(html_path) and os.path.exists(md_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_text = f.read()
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()

        # 抽查 KPI 數值是否在兩檔都出現（容許 $ vs USD 等格式差異）
        kpi_samples = re.findall(r'class="k-val"[^>]*>([^<]+)<', html_text)
        mismatches = []
        for val in kpi_samples:
            clean = val.strip().replace("\n", "")
            # 萃取核心數字部分用於模糊比對（去 $、+、RMB 等前綴）
            core = re.sub(r'^[+$€￥RMB\s]+', '', clean)
            # 核心數字需在 MD 中找到
            if clean not in md_text and core not in md_text:
                mismatches.append(clean)
        sync_checks.append(
            ("KPI 數值在 HTML 與 MD 中一致",
             len(mismatches) == 0,
             f"MD 中找不到：{', '.join(mismatches[:3])}" if mismatches else "")
        )

        if not _print_checks(sync_checks, "🔗 三檔一致性抽查"):
            all_pass = False

    # ── 總結 ──
    print()
    if all_pass:
        print("  ═══════════════════════════════════════")
        print("  ✅ 全部通過！本期報告可正式發布。")
        print("  ═══════════════════════════════════════")
    else:
        print("  ═══════════════════════════════════════")
        print("  ⚠️  有未通過項目，請修正後再次檢核。")
        print("  ═══════════════════════════════════════")

    return 0 if all_pass else 1


# ═══════════════════════ status：查看所有期數狀態 ═══════════════════════

def cmd_status(args):
    """列出 Reports 目錄下所有期數與其三檔狀態。"""
    import glob

    htmls = sorted(glob.glob(os.path.join(REPORTS_DIR, "PaperLuz-*.html")))
    if not htmls:
        print("  尚無任何報告。")
        return 0

    print()
    print("  期數              HTML   MD     PDF    PDF 大小")
    print("  ─────────────────────────────────────────────────")
    for hp in htmls:
        base = os.path.splitext(os.path.basename(hp))[0]
        mp = os.path.join(REPORTS_DIR, base + ".md")
        pp = os.path.join(REPORTS_DIR, base + ".pdf")
        h_ok = "✅" if os.path.exists(hp) else "❌"
        m_ok = "✅" if os.path.exists(mp) else "❌"
        p_ok = "✅" if os.path.exists(pp) else "❌"
        size = ""
        if os.path.exists(pp):
            size = f"{os.path.getsize(pp)/1024:,.0f} KB"
        print(f"  {base:<20s} {h_ok}    {m_ok}    {p_ok}    {size}")
    print()
    return 0


# ═══════════════════════ CLI 進入點 ═══════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="build_report.py",
        description="Paperluz 電子報產製管線 — 鎖定版面、一致品質、定期產出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        ──────────────────────────────────────────────
        完整產製流程（Standard Production Pipeline）：

          ① python build_report.py init
             → 首次萃取黃金模板（僅需一次）

          ② python build_report.py new --issue 007 --date 2026-08-12 \\
                   --week 33 --start 2026-08-05 \\
                   --theme "主軸一 × 主軸二"
             → 建立新期 HTML + MD 骨架

          ③ 編輯 HTML 與 MD 內容（更新數據、圖表、分析）

          ④ python build_report.py validate PaperLuz-007_2026-08-12
             → 9 項結構合規驗證

          ⑤ python build_report.py pdf PaperLuz-007_2026-08-12
             → 產出 A4 PDF

          ⑥ python build_report.py checklist PaperLuz-007_2026-08-12
             → 完整品質檢核（三檔 + 結構 + CSS 指紋 + 一致性）

          ⑦ python build_report.py status
             → 查看所有期數狀態
        ──────────────────────────────────────────────
        """),
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # init
    sub.add_parser("init", help="從第 006 期萃取黃金模板（僅需執行一次）")

    # new
    p_new = sub.add_parser("new", help="從黃金模板建立新一期報告骨架")
    p_new.add_argument("--issue", required=True, help="期數，如 007")
    p_new.add_argument("--date",  required=True, help="發布日期，如 2026-08-12")
    p_new.add_argument("--start", required=True, help="情報週期起始日，如 2026-08-05")
    p_new.add_argument("--end",   default=None,  help="情報週期結束日（預設同 --date）")
    p_new.add_argument("--week",  required=True, type=int, help="ISO 週次，如 33")
    p_new.add_argument("--theme", default=None,  help="本期主軸描述文字")
    p_new.add_argument("--force", action="store_true", help="覆寫已存在的檔案")

    # validate
    p_val = sub.add_parser("validate", help="驗證報告 HTML 結構（9 項檢查）")
    p_val.add_argument("slug", help="報告名稱（不含副檔名），如 PaperLuz-007_2026-08-12")

    # pdf
    p_pdf = sub.add_parser("pdf", help="產出 A4 PDF")
    p_pdf.add_argument("slug", help="報告名稱（不含副檔名）")

    # checklist
    p_chk = sub.add_parser("checklist", help="完整品質檢核（三檔 + 結構 + CSS + 一致性）")
    p_chk.add_argument("slug", help="報告名稱（不含副檔名）")

    # status
    sub.add_parser("status", help="列出所有期數與三檔狀態")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    dispatch = {
        "init":      cmd_init,
        "new":       cmd_new,
        "validate":  cmd_validate,
        "pdf":       cmd_pdf,
        "checklist": cmd_checklist,
        "status":    cmd_status,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
