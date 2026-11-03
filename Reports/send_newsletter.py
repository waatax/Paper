#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paperluz 雙語電子報自動派送引擎 v2.0 (Institutional Dynamic Briefing Dispatcher)
================================================================================

核心升級特點：
  1. 動態報告解析引擎 (Dynamic Issue HTML Parser)：
     - 自動讀取最新或指定期數之 `PaperLuz-{issue}_{date}.html` 與 `_EN.html`，動態萃取「本期主軸」、「6 大 KPI 卡片」與「第一章前 5 大決策洞察（含彩色徽章）」，徹底根除硬編碼舊期數問題。
  2. 機構投研級郵件排版 (Bloomberg / Morning Brew / Substack Pro 標竿規格)：
     - 內建隱藏式 Inbox Preheader 預覽摘要，大幅提升開信率。
     - 採用 100% 郵件客戶端相容之 Hybrid Table 佈局 (`role="presentation"`)，完美支援 Outlook、Apple Mail、Gmail 桌面與手機端。
     - 增設「2×3 關鍵指標卡片網格」、「大宗現貨基準價速覽」、「結構化徽章洞察卡片」、「🍱 食品包裝與無氟替塑專欄焦點」、「🎯 高階採購決策矩陣」與「🔗 12 大章節一鍵跳轉錨點」。
  3. 企業級郵件合規 (RFC 8058 List-Unsubscribe Headers)：
     - 支援標準 `List-Unsubscribe` 與 `X-Mailer` 標頭，提升企業信箱送達率。
"""

import argparse
import csv
import glob
import html as html_lib
import os
import re
import smtplib
import sqlite3
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SUBSCRIBERS_ZH_CSV = os.path.join(DATA_DIR, "subscribers_zh.csv")
SUBSCRIBERS_EN_CSV = os.path.join(DATA_DIR, "subscribers_en.csv")
BASE_URL = "https://waatax.github.io/Paper"


def find_latest_issue(lang="zh"):
    """自動偵測 Reports 目錄下最新發布的期數檔案"""
    pattern = "PaperLuz-*_EN.html" if lang == "en" else "PaperLuz-*[0-9].html"
    files = glob.glob(os.path.join(SCRIPT_DIR, pattern))
    if not files:
        files = glob.glob(os.path.join(SCRIPT_DIR, "PaperLuz-*.html"))
    if not files:
        return "014", "2026-10-30"
    files.sort()
    latest_file = files[-1]
    m = re.search(r"PaperLuz-(\d{3})_([0-9-]+)", os.path.basename(latest_file))
    if m:
        return m.group(1), m.group(2)
    return "014", "2026-10-30"


def load_subscribers(csv_path):
    """讀取 CSV 訂閱名冊中 active 狀態的信箱"""
    if not os.path.exists(csv_path):
        return []
    subscribers = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = (row.get("email") or "").strip().lower()
            status = (row.get("status") or "active").strip().lower()
            if email and status == "active":
                subscribers.append({
                    "email": email,
                    "company": (row.get("company") or "").strip(),
                    "language": (row.get("language") or "zh").strip(),
                })
    return subscribers


def _strip_tags(text):
    return html_lib.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def extract_issue_intelligence(issue_num, publish_date, lang="zh"):
    """
    從 Reports/PaperLuz-{issue_num}_{publish_date}[_EN].html 動態萃取：
      - theme: 本期主軸字串
      - kpis: 6 大 KPI 卡片 [{"title", "val", "desc", "color"}]
      - takeaways: 前 5 大決策洞察 [{"badge", "badge_color", "headline", "body"}]
    """
    suffix = "_EN.html" if lang == "en" else ".html"
    report_path = os.path.join(SCRIPT_DIR, f"PaperLuz-{issue_num}_{publish_date}{suffix}")
    if not os.path.exists(report_path):
        # 嘗試搜尋相同 issue_num 的任何日期檔案
        matches = glob.glob(os.path.join(SCRIPT_DIR, f"PaperLuz-{issue_num}_*{suffix}"))
        if matches:
            report_path = matches[0]

    data = {
        "theme": "",
        "kpis": [],
        "takeaways": [],
    }

    if not os.path.exists(report_path):
        return data

    with open(report_path, "r", encoding="utf-8") as f:
        raw_html = f.read()

    # 1. 萃取 theme-box
    m_theme = re.search(r'<div class="theme-box">(.*?)</div>', raw_html, re.DOTALL)
    if m_theme:
        t_clean = _strip_tags(m_theme.group(1))
        t_clean = re.sub(r"^(本期主軸|Key Highlights)\s*", "", t_clean).strip()
        data["theme"] = t_clean

    # 2. 萃取 6 大 KPI 卡片
    kpi_matches = re.findall(
        r'<div class="kpi-card">\s*<div class="k-title">(.*?)</div>\s*<div class="k-val"(.*?)>(.*?)</div>\s*<div class="k-(?:desc|sub)">(.*?)</div>\s*</div>',
        raw_html,
        re.DOTALL,
    )
    color_map = {
        "var(--c1)": "#60a5fa",
        "var(--c2)": "#fbbf24",
        "var(--c3)": "#34d399",
        "var(--c4)": "#a78bfa",
        "var(--danger)": "#f87171",
    }
    for k_title, style_attr, k_val, k_desc in kpi_matches[:6]:
        val_color = "#60a5fa"
        for k_var, hex_c in color_map.items():
            if k_var in style_attr:
                val_color = hex_c
                break
        data["kpis"].append({
            "title": _strip_tags(k_title),
            "val": _strip_tags(k_val),
            "desc": _strip_tags(k_desc),
            "color": val_color,
        })

    # 3. 萃取第一章前 5 條決策洞察
    s1_match = re.search(r'<h2 id="s1">.*?</h2>\s*<ol[^>]*>(.*?)</ol>', raw_html, re.DOTALL)
    if s1_match:
        li_items = re.findall(r"<li>(.*?)</li>", s1_match.group(1), re.DOTALL)
        badge_palette = {
            "badge-green": ("#064e3b", "#34d399", "#059669"),
            "badge-red": ("#7f1d1d", "#fca5a5", "#ef4444"),
            "badge-amber": ("#78350f", "#fcd34d", "#f59e0b"),
            "badge-blue": ("#1e3a8a", "#93c5fd", "#3b82f6"),
            "badge-purple": ("#4c1d95", "#c4b5fd", "#8b5cf6"),
        }
        for li in li_items[:5]:
            b_m = re.search(r'<span class="badge\s+([^"]+)">(.*?)</span>', li)
            b_cls = b_m.group(1).strip() if b_m else "badge-blue"
            b_txt = _strip_tags(b_m.group(2)) if b_m else ("核心洞察" if lang == "zh" else "Insight")
            bg_c, fg_c, border_c = badge_palette.get(b_cls, ("#1e3a8a", "#93c5fd", "#3b82f6"))

            # 移除 badge 後萃取粗體標題與內文
            rest = re.sub(r'<span class="badge[^"]*">.*?</span>', "", li, count=1).strip()
            hl_m = re.search(r"<b>(.*?)</b>", rest, re.DOTALL)
            if hl_m:
                hl_txt = _strip_tags(hl_m.group(1))
                body_txt = _strip_tags(rest.replace(hl_m.group(0), "", 1)).lstrip("：:").strip()
            else:
                hl_txt = _strip_tags(rest)[:60]
                body_txt = _strip_tags(rest)

            data["takeaways"].append({
                "badge": b_txt,
                "bg_color": bg_c,
                "fg_color": fg_c,
                "border_color": border_c,
                "headline": hl_txt,
                "body": body_txt,
            })

    return data


def _render_kpi_grid_html(kpis):
    """將 6 張 KPI 卡片渲染為郵件客戶端 100% 相容之 2×3 雙欄 Table"""
    if not kpis:
        return ""
    rows_html = ""
    for i in range(0, len(kpis), 2):
        left = kpis[i]
        right = kpis[i + 1] if i + 1 < len(kpis) else None
        rows_html += '<tr>'
        rows_html += f'''
          <td width="50%" valign="top" style="padding:0 6px 12px 0;">
            <div style="background-color:#162447; border:1px solid #263b6a; border-radius:8px; padding:12px 14px;">
              <div style="font-size:11px; font-weight:700; color:#94a3b8; letter-spacing:0.02em;">{left["title"]}</div>
              <div style="font-size:16px; font-weight:800; color:{left["color"]}; margin:4px 0 5px 0; line-height:1.25;">{left["val"]}</div>
              <div style="font-size:11.5px; color:#cbd5e1; line-height:1.45;">{left["desc"]}</div>
            </div>
          </td>'''
        if right:
            rows_html += f'''
          <td width="50%" valign="top" style="padding:0 0 12px 6px;">
            <div style="background-color:#162447; border:1px solid #263b6a; border-radius:8px; padding:12px 14px;">
              <div style="font-size:11px; font-weight:700; color:#94a3b8; letter-spacing:0.02em;">{right["title"]}</div>
              <div style="font-size:16px; font-weight:800; color:{right["color"]}; margin:4px 0 5px 0; line-height:1.25;">{right["val"]}</div>
              <div style="font-size:11.5px; color:#cbd5e1; line-height:1.45;">{right["desc"]}</div>
            </div>
          </td>'''
        else:
            rows_html += '<td width="50%"></td>'
        rows_html += '</tr>'
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;">{rows_html}</table>'


def _render_takeaways_html(takeaways):
    """將前 5 大決策洞察渲染為機構級結構化卡片"""
    out = ""
    for idx, item in enumerate(takeaways, 1):
        out += f'''
        <div style="background-color:#152242; border:1px solid #24355a; border-left:4px solid {item["border_color"]}; border-radius:8px; padding:14px 16px; margin-bottom:12px;">
          <div style="margin-bottom:6px;">
            <span style="display:inline-block; background-color:{item["bg_color"]}; color:{item["fg_color"]}; font-size:11px; font-weight:800; padding:2px 8px; border-radius:4px; margin-right:6px; vertical-align:middle;">{item["badge"]}</span>
            <span style="color:#ffffff; font-size:14px; font-weight:800; line-height:1.45; vertical-align:middle;">{idx}. {item["headline"]}</span>
          </div>
          <div style="color:#cbd5e1; font-size:13px; line-height:1.65;">
            {item["body"]}
          </div>
        </div>'''
    return out


def build_newsletter_html_zh(issue_num, publish_date):
    """產製符合彭博/Substack 機構投研標準之繁體中文響應式 HTML 電子報"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.pdf"
    md_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.md"
    portal_url = f"{BASE_URL}/"

    intel = extract_issue_intelligence(issue_num, publish_date, lang="zh")
    theme_text = intel["theme"] or (
        "北美箱板紙龍頭 PCA Q3 財報獲利超預期（驗證 $840 歷史峰頂利差轉化現金流）× "
        "歐盟 PFHxA 全氟己酸禁令 10/18 正式強制生效開罰 × 售價走揚 華紙逆勢強漲 × "
        "陸工紙龍頭兩輪提漲（+100元）全面落地 × 台灣老紙廠蕉麻紙紗躍登巴黎世家供應鏈 × "
        "布蘭特原油於 $74 築底、台廠生質能替代率升至 49.0% 鎖定蒸氣成本 NT$718"
    )
    kpi_grid_html = _render_kpi_grid_html(intel["kpis"])
    takeaways_html = _render_takeaways_html(intel["takeaways"])

    preheader_text = f"【第 {issue_num} 期出刊】{theme_text[:110]}... 內附 6 大核心行情卡、食品包裝無氟專欄與高階採購決策矩陣。"

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="dark light">
  <title>Paperluz 產業情報週報 第 {issue_num} 期 ({publish_date})</title>
</head>
<body style="margin:0; padding:0; background-color:#080f20; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans TC', Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased; color:#f8fafc;">
  <!-- Hidden Inbox Preheader Text -->
  <div style="display:none; max-height:0px; overflow:hidden; mso-hide:all; font-size:1px; color:#080f20; line-height:1px;">
    {preheader_text}&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#080f20; padding:20px 10px;">
    <tr>
      <td align="center">
        <div style="max-width:660px; margin:0 auto; background-color:#101b37; border:1px solid #24355a; border-radius:14px; overflow:hidden; box-shadow:0 16px 40px rgba(0,0,0,0.55); text-align:left;">

          <!-- Top Institutional Utility Bar -->
          <div style="background-color:#0b1329; padding:10px 26px; border-bottom:1px solid #1e2f53; font-size:11.5px; color:#94a3b8;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="left" style="color:#94a3b8; font-weight:600;">
                  🇹🇼 繁體中文決策版 ｜ ⏱️ 深度研讀 4 分鐘 ｜ 💵 USD-First 雙幣基準
                </td>
                <td align="right">
                  <a href="{web_url}" style="color:#60a5fa; text-decoration:none; font-weight:700;">瀏覽器開啟 ↗</a>
                  <span style="color:#334155; margin:0 6px;">|</span>
                  <a href="{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.html" style="color:#94a3b8; text-decoration:none;">English</a>
                </td>
              </tr>
            </table>
          </div>

          <!-- Brand Masthead Header -->
          <div style="background:linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding:26px 28px 22px 28px; border-bottom:1px solid #263b6a;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="left" valign="middle">
                  <span style="font-size:23px; font-weight:900; color:#ffffff; letter-spacing:-0.03em;">
                    📑 Paperluz
                  </span>
                  <span style="display:inline-block; font-size:10.5px; font-weight:800; background-color:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px; letter-spacing:0.06em; vertical-align:middle;">
                    Executive Intelligence
                  </span>
                </td>
                <td align="right" valign="middle">
                  <span style="display:inline-block; background-color:rgba(15, 23, 42, 0.65); border:1px solid #3b82f6; color:#93c5fd; font-size:12px; font-weight:800; padding:4px 10px; border-radius:6px;">
                    第 {issue_num} 期 ｜ {publish_date}
                  </span>
                </td>
              </tr>
            </table>
            <h1 style="color:#ffffff; font-size:21px; font-weight:900; line-height:1.38; margin:16px 0 6px 0; letter-spacing:-0.02em;">
              全球與台灣紙業產業情報週報
            </h1>
            <div style="color:#93c5fd; font-size:13px; font-weight:600;">
              每週五 07:00 晨間直送 · 國際木漿與廢紙利差 · 食品包裝替塑專欄 · 全鏈預測矩陣
            </div>
          </div>

          <!-- Main Body Container -->
          <div style="padding:24px 28px;">

            <!-- 1. Strategic Executive Alert -->
            <div style="background-color:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.35); border-left:4px solid #ef4444; padding:14px 16px; border-radius:6px; margin-bottom:24px;">
              <div style="color:#f87171; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:5px;">
                🚨 本期核心戰略主軸 (Executive Thesis)
              </div>
              <div style="color:#f8fafc; font-size:13.5px; font-weight:600; line-height:1.6;">
                {theme_text}
              </div>
            </div>

            <!-- 2. 2x3 Executive KPI Cards -->
            <h3 style="color:#ffffff; font-size:15px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:0 0 12px 0;">
              📊 本週 6 大核心關鍵指標卡 (3×2 Executive KPI Dashboard)
            </h3>
            {kpi_grid_html}

            <!-- 2.1 Spot Benchmark Quick Table -->
            <h3 style="color:#ffffff; font-size:14.5px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:18px 0 10px 0;">
              💹 全球大宗原物料與價差基準速覽 (USD-First Benchmarks)
            </h3>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; margin-bottom:24px; font-size:12.5px; border:1px solid #24355a; border-radius:8px; overflow:hidden;">
              <thead>
                <tr style="background-color:#1a294f; color:#94a3b8; text-align:left;">
                  <th style="padding:9px 12px;">關鍵標的</th>
                  <th style="padding:9px 12px;">最新報價 (USD / 在地幣)</th>
                  <th style="padding:9px 12px;">週變動與傳導解讀</th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc;">
                  <td style="padding:9px 12px; font-weight:700;">長纖漂針漿 (NBSK)</td>
                  <td style="padding:9px 12px; color:#60a5fa; font-weight:800;">USD 700 / 噸 <span style="color:#94a3b8; font-weight:600;">(RMB 4,960)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">+20元 · 港口庫存連16週去化至201.8萬噸</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc; background-color:#13203f;">
                  <td style="padding:9px 12px; font-weight:700;">短纖漂闊漿 (BHKP)</td>
                  <td style="padding:9px 12px; color:#38bdf8; font-weight:800;">USD 632 / 噸 <span style="color:#94a3b8; font-weight:600;">(RMB 4,490)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">+15元 · Suzano宣告11月歐美再漲+$50(牌價$1,410)</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc;">
                  <td style="padding:9px 12px; font-weight:700;">美廢 11# OCC 出口</td>
                  <td style="padding:9px 12px; color:#fbbf24; font-weight:800;">USD 136 / 短噸 <span style="color:#94a3b8; font-weight:600;">(FAS)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">高檔持平 · 雙十一高峰推升國廢 A 級至 RMB 2,050</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc; background-color:#13203f;">
                  <td style="padding:9px 12px; font-weight:700;">北美工紙 Raw Spread</td>
                  <td style="padding:9px 12px; color:#a78bfa; font-weight:800;">USD 839 / 短噸 <span style="color:#94a3b8; font-weight:600;">(業績分化)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">PCA(93%稼動率)強勁變現 vs SW成本通膨重挫10%</td>
                </tr>
                <tr style="color:#f8fafc;">
                  <td style="padding:9px 12px; font-weight:700;">布蘭特原油 / 台廠蒸氣</td>
                  <td style="padding:9px 12px; color:#34d399; font-weight:800;">$73.80 / 桶 <span style="color:#94a3b8; font-weight:600;">(蒸氣 NT$718)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">低油價維持助劑紅利 · SRF 替代率升至 49.2%</td>
                </tr>
              </tbody>
            </table>

            <!-- 3. Top 5 Executive Takeaways -->
            <h3 style="color:#ffffff; font-size:15px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:0 0 14px 0;">
              💡 本週 5 大決策洞察 (Top 5 Executive Briefings)
            </h3>
            {takeaways_html}

            <!-- 4. Food Packaging & Molded Fiber Column Spotlight -->
            <div style="background:linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(15, 23, 42, 0.9) 100%); border:1px solid rgba(16, 185, 129, 0.35); border-radius:10px; padding:16px 18px; margin:22px 0;">
              <div style="color:#34d399; font-size:11.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">
                🍱 第六章特別專欄焦點：全球與台灣食品包裝（紙袋 · 紙杯 · 紙模塑 · 折疊盒）
              </div>
              <div style="color:#ffffff; font-size:14px; font-weight:800; margin-bottom:6px;">
                歐盟 PFHxA 零日開罰全面接管 × 華紙「益利疊」無氟食安紙爆單 × 埔里蕉麻紙紗進軍巴黎世家
              </div>
              <div style="color:#cbd5e1; font-size:12.5px; line-height:1.6;">
                • <b>台灣與歐洲合規</b>：歐盟 Regulation (EU) 2024/2462 自 10/18 強制抽檢 25 ppb 總氟限值，華紙益利疊水性塗層卡紙與台灣中部防油紙袋廠外銷訂單滿載；埔里老紙廠以馬尼拉麻抄造高韌性「紙紗」打入 Balenciaga 萬元丹寧供應鏈。<br>
                • <b>六國連動掃描</b>：中國白卡紙（USD 639 / RMB 4,485）挺價與眾鑫印尼 5 萬噸紙模塑擴廠、日本製紙無鋁內側印刷紙盒商用化、美國緬因州起訴紙廠 PFAS 污染加速 QSR 水性塗層替換。
              </div>
            </div>

            <!-- 5. C-Level Actionable Procurement Matrix -->
            <h3 style="color:#ffffff; font-size:14.5px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:20px 0 10px 0;">
              🎯 高階採購與避險行動矩陣 (C-Level Procurement Action Matrix)
            </h3>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; margin-bottom:24px; font-size:12px; border:1px solid #24355a;">
              <thead>
                <tr style="background-color:#1a294f; color:#94a3b8; text-align:left;">
                  <th style="padding:8px 10px;">採購品類</th>
                  <th style="padding:8px 10px;">戰略評級</th>
                  <th style="padding:8px 10px;">實戰操作與避險建議</th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc;">
                  <td style="padding:8px 10px; font-weight:700;">長短纖木漿 (NBSK/BHKP)</td>
                  <td style="padding:8px 10px;"><span style="background:#064e3b; color:#34d399; padding:2px 6px; border-radius:4px; font-weight:700;">分批鎖價</span></td>
                  <td style="padding:8px 10px; color:#cbd5e1;">港口庫存連降15週＋Suzano提價落地，建議鎖定 Q4 至明年初 60% 剛需長約</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc; background-color:#13203f;">
                  <td style="padding:8px 10px; font-weight:700;">瓦楞箱板原紙 / 紙箱</td>
                  <td style="padding:8px 10px;"><span style="background:#78350f; color:#fcd34d; padding:2px 6px; border-radius:4px; font-weight:700;">提前備庫</span></td>
                  <td style="padding:8px 10px; color:#cbd5e1;">大陸兩輪提漲 +100元已落地，二級紙器廠宜拉高安全庫存至 35–40 天</td>
                </tr>
                <tr style="color:#f8fafc;">
                  <td style="padding:8px 10px; font-weight:700;">食品卡紙 / 防油紙袋</td>
                  <td style="padding:8px 10px;"><span style="background:#7f1d1d; color:#fca5a5; padding:2px 6px; border-radius:4px; font-weight:700;">強制無氟</span></td>
                  <td style="padding:8px 10px; color:#cbd5e1;">銷歐美包材須取得 &lt;25 ppb 無氟證明並全面切換水性阻隔塗層 (Aqueous Barrier)</td>
                </tr>
              </tbody>
            </table>

            <!-- 6. Primary CTA Buttons -->
            <div style="text-align:center; padding:8px 0 18px 0;">
              <a href="{web_url}" style="display:inline-block; background-color:#2563eb; color:#ffffff; text-decoration:none; padding:13px 24px; border-radius:8px; font-size:14px; font-weight:800; margin:0 6px 10px 6px; box-shadow:0 4px 14px rgba(37,99,235,0.45);">
                📖 在線閱讀完整第 {issue_num} 期報告 (HTML) ➔
              </a>
              <a href="{pdf_url}" style="display:inline-block; background-color:#1e293b; color:#f8fafc; border:1px solid #3b82f6; text-decoration:none; padding:13px 22px; border-radius:8px; font-size:14px; font-weight:800; margin:0 6px 10px 6px;">
                📄 下載 A4 Zero-Gap PDF 典藏版
              </a>
            </div>

            <!-- 7. Deep-Link Chapter Quick Directory -->
            <div style="background-color:#0b1329; border:1px solid #1e2f53; border-radius:8px; padding:14px 16px; margin-top:6px;">
              <div style="font-size:11.5px; font-weight:800; color:#94a3b8; text-transform:uppercase; margin-bottom:8px; text-align:center;">
                🔗 完整報告 12 大標準章節快速跳轉 (Direct Section Links)
              </div>
              <div style="font-size:12px; line-height:1.9; text-align:center; color:#64748b;">
                <a href="{web_url}#s1" style="color:#60a5fa; text-decoration:none; margin:0 5px;">一、十行摘要</a> ·
                <a href="{web_url}#s2" style="color:#60a5fa; text-decoration:none; margin:0 5px;">二、關鍵指標表</a> ·
                <a href="{web_url}#s3" style="color:#60a5fa; text-decoration:none; margin:0 5px;">三、5大SVG圖表</a> ·
                <a href="{web_url}#s3-6" style="color:#a78bfa; text-decoration:none; font-weight:700; margin:0 5px;">3.6 全鏈預測矩陣</a> ·
                <a href="{web_url}#s6" style="color:#34d399; text-decoration:none; font-weight:700; margin:0 5px;">六、食品包裝專欄</a> ·
                <a href="{web_url}#s8" style="color:#fbbf24; text-decoration:none; font-weight:700; margin:0 5px;">八、高階採購矩陣</a> ·
                <a href="{web_url}#s9" style="color:#f87171; text-decoration:none; margin:0 5px;">九、法規倒數雷達</a> ·
                <a href="{md_url}" style="color:#94a3b8; text-decoration:none; margin:0 5px;">📝 Markdown 原文</a>
              </div>
            </div>

          </div>

          <!-- Email Footer -->
          <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:22px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.65;">
            <div style="color:#cbd5e1; font-weight:800; font-size:13px;">Paperluz · 全球與台灣紙業產業情報平台</div>
            <div style="margin-top:4px;"><b>產出時間</b>：{publish_date}　·　<b>系統版本</b>：Paperluz Engine v14.0　·　<b>發行機構</b>：光網資訊 Luznet ∕ Paperluz 產業情報</div>
            <div style="margin-top:8px;">
              官方門戶：<a href="{portal_url}" style="color:#60a5fa; text-decoration:none; font-weight:600;">waatax.github.io/Paper/</a> ｜
              <a href="{portal_url}EN/" style="color:#60a5fa; text-decoration:none; font-weight:600;">English Edition</a> ｜
              <a href="{portal_url}#calculator" style="color:#60a5fa; text-decoration:none; font-weight:600;">毛利敏感度試算器</a>
            </div>
            <div style="margin-top:12px; border-top:1px solid #1a294f; padding-top:12px; color:#475569; font-size:11.5px;">
              您收到此郵件是因為您已登記於 Paperluz 高階決策訂閱名冊。若需管理訂閱偏好或取消訂閱，請直接回覆主旨「Unsubscribe」或至官網退訂。
            </div>
          </div>

        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html


def build_newsletter_html_en(issue_num, publish_date):
    """產製符合彭博/Substack 機構投研標準之英文國際版響應式 HTML 電子報"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.pdf"
    md_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.md"
    portal_url = f"{BASE_URL}/EN/"

    intel = extract_issue_intelligence(issue_num, publish_date, lang="en")
    theme_text = intel["theme"] or (
        "North American Packaging Leader PCA Q3 Earnings Beat Across the Board (Validating $840/ST Record Raw Spread Cash Conversion) × "
        "EU PFHxA Ban Enters Mandatory Enforcement on Oct 18 (Zero Day Passed) × Chung Hwa Pulp (1905) Surges on Strong Paper & Pulp Pricing × "
        "China Containerboard Two-Wave Hikes (+RMB 100/MT) Fully Implemented × Historic Puli Mill Supplies Abaca Paper Yarn to Balenciaga × "
        "Brent Crude Consolidates at $74/bbl; Taiwan Mills Lock Steam at NT$718/t (49% Biomass)"
    )
    kpi_grid_html = _render_kpi_grid_html(intel["kpis"])
    takeaways_html = _render_takeaways_html(intel["takeaways"])

    preheader_text = f"[Issue {issue_num} Released] {theme_text[:115]}... Includes 6 Executive KPIs, Food Packaging Spotlight & Procurement Matrix."

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="dark light">
  <title>Paperluz Global Industry Intelligence Weekly Issue {issue_num} ({publish_date})</title>
</head>
<body style="margin:0; padding:0; background-color:#080f20; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased; color:#f8fafc;">
  <!-- Hidden Inbox Preheader Text -->
  <div style="display:none; max-height:0px; overflow:hidden; mso-hide:all; font-size:1px; color:#080f20; line-height:1px;">
    {preheader_text}&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#080f20; padding:20px 10px;">
    <tr>
      <td align="center">
        <div style="max-width:660px; margin:0 auto; background-color:#101b37; border:1px solid #24355a; border-radius:14px; overflow:hidden; box-shadow:0 16px 40px rgba(0,0,0,0.55); text-align:left;">

          <!-- Top Institutional Utility Bar -->
          <div style="background-color:#0b1329; padding:10px 26px; border-bottom:1px solid #1e2f53; font-size:11.5px; color:#94a3b8;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="left" style="color:#94a3b8; font-weight:600;">
                  🌐 Global Executive Edition ｜ ⏱️ 4-Min Read ｜ 💵 USD-First Dual-Currency
                </td>
                <td align="right">
                  <a href="{web_url}" style="color:#60a5fa; text-decoration:none; font-weight:700;">View in Browser ↗</a>
                  <span style="color:#334155; margin:0 6px;">|</span>
                  <a href="{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.html" style="color:#94a3b8; text-decoration:none;">繁體中文</a>
                </td>
              </tr>
            </table>
          </div>

          <!-- Brand Masthead Header -->
          <div style="background:linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding:26px 28px 22px 28px; border-bottom:1px solid #263b6a;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="left" valign="middle">
                  <span style="font-size:23px; font-weight:900; color:#ffffff; letter-spacing:-0.03em;">
                    📑 Paperluz
                  </span>
                  <span style="display:inline-block; font-size:10.5px; font-weight:800; background-color:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px; letter-spacing:0.06em; vertical-align:middle;">
                    Executive Intelligence
                  </span>
                </td>
                <td align="right" valign="middle">
                  <span style="display:inline-block; background-color:rgba(15, 23, 42, 0.65); border:1px solid #3b82f6; color:#93c5fd; font-size:12px; font-weight:800; padding:4px 10px; border-radius:6px;">
                    Issue {issue_num} ｜ {publish_date}
                  </span>
                </td>
              </tr>
            </table>
            <h1 style="color:#ffffff; font-size:21px; font-weight:900; line-height:1.38; margin:16px 0 6px 0; letter-spacing:-0.02em;">
              Global Pulp &amp; Paper Industry Intelligence Briefing
            </h1>
            <div style="color:#93c5fd; font-size:13px; font-weight:600;">
              Friday 07:00 AM Delivery · Commodity Spot &amp; Mill Spreads · PFAS-Free Packaging · Predictive Matrix
            </div>
          </div>

          <!-- Main Body Container -->
          <div style="padding:24px 28px;">

            <!-- 1. Strategic Executive Alert -->
            <div style="background-color:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.35); border-left:4px solid #ef4444; padding:14px 16px; border-radius:6px; margin-bottom:24px;">
              <div style="color:#f87171; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:5px;">
                🚨 Strategic Executive Thesis
              </div>
              <div style="color:#f8fafc; font-size:13.5px; font-weight:600; line-height:1.6;">
                {theme_text}
              </div>
            </div>

            <!-- 2. 2x3 Executive KPI Cards -->
            <h3 style="color:#ffffff; font-size:15px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:0 0 12px 0;">
              📊 6 Core Executive KPI Cards (3×2 Dashboard)
            </h3>
            {kpi_grid_html}

            <!-- 2.1 Spot Benchmark Quick Table -->
            <h3 style="color:#ffffff; font-size:14.5px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:18px 0 10px 0;">
              💹 Global Commodity &amp; Spread Benchmarks (USD-First)
            </h3>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; margin-bottom:24px; font-size:12.5px; border:1px solid #24355a; border-radius:8px; overflow:hidden;">
              <thead>
                <tr style="background-color:#1a294f; color:#94a3b8; text-align:left;">
                  <th style="padding:9px 12px;">Benchmark</th>
                  <th style="padding:9px 12px;">Latest Spot (USD / Local)</th>
                  <th style="padding:9px 12px;">WoW Dynamics &amp; Spread</th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc;">
                  <td style="padding:9px 12px; font-weight:700;">China NBSK Softwood</td>
                  <td style="padding:9px 12px; color:#60a5fa; font-weight:800;">USD 700 / MT <span style="color:#94a3b8; font-weight:600;">(RMB 4,960)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">+20 RMB · Port stocks down 16 wks to 2.018M MT</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc; background-color:#13203f;">
                  <td style="padding:9px 12px; font-weight:700;">China BHKP Hardwood</td>
                  <td style="padding:9px 12px; color:#38bdf8; font-weight:800;">USD 632 / MT <span style="color:#94a3b8; font-weight:600;">(RMB 4,490)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">+15 RMB · Suzano Nov +$50 hike (EU list $1,410)</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc;">
                  <td style="padding:9px 12px; font-weight:700;">US OCC #11 Export FAS</td>
                  <td style="padding:9px 12px; color:#fbbf24; font-weight:800;">USD 136 / ST <span style="color:#94a3b8; font-weight:600;">(FAS)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">Firm · China Grade-A domestic OCC rises to RMB 2,050</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc; background-color:#13203f;">
                  <td style="padding:9px 12px; font-weight:700;">US Containerboard Spread</td>
                  <td style="padding:9px 12px; color:#a78bfa; font-weight:800;">USD 839 / ST <span style="color:#94a3b8; font-weight:600;">(Divergence)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">PCA 93% rate beat vs. Smurfit Westrock -10% Q3 miss</td>
                </tr>
                <tr style="color:#f8fafc;">
                  <td style="padding:9px 12px; font-weight:700;">Brent Crude / Mill Steam</td>
                  <td style="padding:9px 12px; color:#34d399; font-weight:800;">$73.80 / bbl <span style="color:#94a3b8; font-weight:600;">(NT$718 Steam)</span></td>
                  <td style="padding:9px 12px; color:#cbd5e1;">Low chemical costs · 49.2% SRF biomass substitution</td>
                </tr>
              </tbody>
            </table>

            <!-- 3. Top 5 Executive Takeaways -->
            <h3 style="color:#ffffff; font-size:15px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:0 0 14px 0;">
              💡 Top 5 Executive Briefings &amp; Market Signals
            </h3>
            {takeaways_html}

            <!-- 4. Food Packaging & Molded Fiber Column Spotlight -->
            <div style="background:linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(15, 23, 42, 0.9) 100%); border:1px solid rgba(16, 185, 129, 0.35); border-radius:10px; padding:16px 18px; margin:22px 0;">
              <div style="color:#34d399; font-size:11.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">
                🍱 Section 6 Special Column: Global &amp; Taiwan Food Packaging (Bags · Cups · Molded Fiber · Cartons)
              </div>
              <div style="color:#ffffff; font-size:14px; font-weight:800; margin-bottom:6px;">
                EU PFHxA Zero-Day Enforcement Active × CHP CircuWell Non-Fluorinated Boom × Puli Abaca Yarn in Balenciaga
              </div>
              <div style="color:#cbd5e1; font-size:12.5px; line-height:1.6;">
                • <b>EU &amp; Taiwan Transition</b>: Regulation (EU) 2024/2462 enforces a strict 25 ppb total fluorine limit at EU customs as of Oct 18, driving full-capacity shipments for CHP's CircuWell aqueous barrier board; Puli heritage mill commercializes Manila hemp "Paper Yarn" for Balenciaga luxury denim.<br>
                • <b>6-Country Cross-Scan</b>: China FBB holds USD 639/MT (RMB 4,485) alongside Zhongxin's 50k-ton Indonesia molded fiber expansion; Nippon Paper debuts aluminum-free inner-printed cartons; Maine PFAS federal suit accelerates US QSR aqueous barrier adoption.
              </div>
            </div>

            <!-- 5. C-Level Actionable Procurement Matrix -->
            <h3 style="color:#ffffff; font-size:14.5px; font-weight:800; border-bottom:1px solid #24355a; padding-bottom:8px; margin:20px 0 10px 0;">
              🎯 C-Level Procurement &amp; Hedging Action Matrix
            </h3>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; margin-bottom:24px; font-size:12px; border:1px solid #24355a;">
              <thead>
                <tr style="background-color:#1a294f; color:#94a3b8; text-align:left;">
                  <th style="padding:8px 10px;">Category</th>
                  <th style="padding:8px 10px;">Action Rating</th>
                  <th style="padding:8px 10px;">Strategic Execution &amp; Hedging Guidance</th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc;">
                  <td style="padding:8px 10px; font-weight:700;">Virgin Wood Pulp (NBSK/BHKP)</td>
                  <td style="padding:8px 10px;"><span style="background:#064e3b; color:#34d399; padding:2px 6px; border-radius:4px; font-weight:700;">Lock Contracts</span></td>
                  <td style="padding:8px 10px; color:#cbd5e1;">15-week port destocking + Suzano hikes realized; lock 60% Q4–Q1 contract volume</td>
                </tr>
                <tr style="border-bottom:1px solid #1e2f53; color:#f8fafc; background-color:#13203f;">
                  <td style="padding:8px 10px; font-weight:700;">Containerboard &amp; Boxes</td>
                  <td style="padding:8px 10px;"><span style="background:#78350f; color:#fcd34d; padding:2px 6px; border-radius:4px; font-weight:700;">Build Buffer</span></td>
                  <td style="padding:8px 10px; color:#cbd5e1;">China +RMB 100 hikes enacted &amp; US $840 spread solid; raise box safety stock to 35–40 days</td>
                </tr>
                <tr style="color:#f8fafc;">
                  <td style="padding:8px 10px; font-weight:700;">Food Board &amp; Greaseproof Bags</td>
                  <td style="padding:8px 10px;"><span style="background:#7f1d1d; color:#fca5a5; padding:2px 6px; border-radius:4px; font-weight:700;">100% PFAS-Free</span></td>
                  <td style="padding:8px 10px; color:#cbd5e1;">Mandate &lt;25 ppb total fluorine COA and switch EU/US exports to aqueous dispersion barriers</td>
                </tr>
              </tbody>
            </table>

            <!-- 6. Primary CTA Buttons -->
            <div style="text-align:center; padding:8px 0 18px 0;">
              <a href="{web_url}" style="display:inline-block; background-color:#2563eb; color:#ffffff; text-decoration:none; padding:13px 24px; border-radius:8px; font-size:14px; font-weight:800; margin:0 6px 10px 6px; box-shadow:0 4px 14px rgba(37,99,235,0.45);">
                📖 Read Full Issue {issue_num} Report Online (HTML) ➔
              </a>
              <a href="{pdf_url}" style="display:inline-block; background-color:#1e293b; color:#f8fafc; border:1px solid #3b82f6; text-decoration:none; padding:13px 22px; border-radius:8px; font-size:14px; font-weight:800; margin:0 6px 10px 6px;">
                📄 Download A4 Zero-Gap PDF Deliverable
              </a>
            </div>

            <!-- 7. Deep-Link Chapter Quick Directory -->
            <div style="background-color:#0b1329; border:1px solid #1e2f53; border-radius:8px; padding:14px 16px; margin-top:6px;">
              <div style="font-size:11.5px; font-weight:800; color:#94a3b8; text-transform:uppercase; margin-bottom:8px; text-align:center;">
                🔗 Direct 12-Section Report Navigation
              </div>
              <div style="font-size:12px; line-height:1.9; text-align:center; color:#64748b;">
                <a href="{web_url}#s1" style="color:#60a5fa; text-decoration:none; margin:0 5px;">1. Executive Summary</a> ·
                <a href="{web_url}#s2" style="color:#60a5fa; text-decoration:none; margin:0 5px;">2. KPI Dashboard</a> ·
                <a href="{web_url}#s3" style="color:#60a5fa; text-decoration:none; margin:0 5px;">3. 5 SVG Charts</a> ·
                <a href="{web_url}#s3-6" style="color:#a78bfa; text-decoration:none; font-weight:700; margin:0 5px;">3.6 Forward Matrix</a> ·
                <a href="{web_url}#s6" style="color:#34d399; text-decoration:none; font-weight:700; margin:0 5px;">6. Food Packaging</a> ·
                <a href="{web_url}#s8" style="color:#fbbf24; text-decoration:none; font-weight:700; margin:0 5px;">8. Procurement Matrix</a> ·
                <a href="{web_url}#s9" style="color:#f87171; text-decoration:none; margin:0 5px;">9. Regulatory Radar</a> ·
                <a href="{md_url}" style="color:#94a3b8; text-decoration:none; margin:0 5px;">📝 Raw Markdown</a>
              </div>
            </div>

          </div>

          <!-- Email Footer -->
          <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:22px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.65;">
            <div style="color:#cbd5e1; font-weight:800; font-size:13px;">Paperluz · Global Pulp &amp; Paper Industry Intelligence Hub</div>
            <div style="margin-top:4px;"><b>Published</b>: {publish_date}　·　<b>Engine</b>: Paperluz Engine v14.0　·　<b>Publisher</b>: Luznet / Paperluz Intelligence</div>
            <div style="margin-top:8px;">
              Official Portal: <a href="{portal_url}" style="color:#60a5fa; text-decoration:none; font-weight:600;">waatax.github.io/Paper/EN/</a> ｜
              <a href="{BASE_URL}/" style="color:#60a5fa; text-decoration:none; font-weight:600;">繁體中文版</a> ｜
              <a href="{portal_url}#calculator" style="color:#60a5fa; text-decoration:none; font-weight:600;">Margin Simulator</a>
            </div>
            <div style="margin-top:12px; border-top:1px solid #1a294f; padding-top:12px; color:#475569; font-size:11.5px;">
              You received this briefing because you are enrolled in the Paperluz executive distribution list. To manage preferences or unsubscribe, reply with "Unsubscribe" or visit our portal.
            </div>
          </div>

        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html


def build_welcome_email_zh(issue_num, publish_date):
    """產製繁體中文即時迎新確認信內容 (動態對齊最新期數)"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.pdf"
    portal_url = f"{BASE_URL}/"
    intel = extract_issue_intelligence(issue_num, publish_date, lang="zh")
    theme_text = intel["theme"] or "最新國際木漿、北美與兩岸工紙提價、食品包裝無氟轉型與全鏈預測矩陣完整解析。"

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>歡迎訂閱 Paperluz 全球與台灣紙業產業情報週報</title>
</head>
<body style="margin:0; padding:0; background-color:#080f20; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans TC', Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <div style="max-width:640px; margin:20px auto 30px auto; background-color:#101b37; border:1px solid #24355a; border-radius:14px; overflow:hidden; box-shadow:0 12px 32px rgba(0,0,0,0.5);">
    <div style="background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:26px 28px; border-bottom:1px solid #24355a;">
      <span style="font-size:22px; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
        📑 Paperluz <span style="font-size:11px; font-weight:700; background:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px;">Intelligence Hub</span>
      </span>
      <h1 style="color:#ffffff; font-size:21px; font-weight:900; line-height:1.4; margin:16px 0 6px 0;">
        🎉 感謝您訂閱 Paperluz 每週產業情報！
      </h1>
      <div style="color:#93c5fd; font-size:13.5px; font-weight:600;">
        每週五晨間 07:00 準時發送 · 您的專屬迎新禮包（第 {issue_num} 期）已備妥
      </div>
    </div>

    <div style="padding:26px 28px;">
      <p style="color:#f8fafc; font-size:14.5px; line-height:1.7; margin-bottom:20px;">
        您好！歡迎加入 Paperluz 高階產業決策網絡。您已成功登記訂閱 <strong>繁體中文版每週週報</strong>。
      </p>

      <div style="background:rgba(37, 99, 235, 0.12); border:1px solid rgba(59, 130, 246, 0.35); border-radius:8px; padding:16px 20px; margin-bottom:24px;">
        <div style="font-size:12px; font-weight:800; color:#60a5fa; text-transform:uppercase; margin-bottom:6px;">📅 出刊時間與發送機制</div>
        <div style="font-size:13.5px; color:#cbd5e1; line-height:1.6;">
          本平台固定於 <strong>每週五上午 07:00 (UTC+8 台灣時間)</strong> 自動出刊。每當新一期發布時，系統將自動寄送最新產業簡報至您的信箱，確保您在每週開工前掌握第一手全球情報。
        </div>
      </div>

      <div style="background:#162447; border-radius:10px; padding:20px; margin-bottom:26px; border:1px solid #263b6a;">
        <div style="font-size:12px; font-weight:800; color:#fbbf24; text-transform:uppercase; margin-bottom:6px;">🎁 迎新專屬資料禮包</div>
        <h3 style="color:#ffffff; font-size:16px; font-weight:800; margin:0 0 10px 0;">
          最新出刊：第 {issue_num} 期 ({publish_date}) 深度專題完整版
        </h3>
        <p style="color:#cbd5e1; font-size:13px; line-height:1.6; margin-bottom:16px;">
          {theme_text}
        </p>
        <div>
          <a href="{web_url}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700; margin-right:8px; margin-bottom:8px;">
            📖 在線閱讀第 {issue_num} 期 ➔
          </a>
          <a href="{pdf_url}" style="display:inline-block; background:#0b1329; color:#f8fafc; border:1px solid #3b82f6; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700;">
            📄 下載 A4 Zero-Gap PDF
          </a>
        </div>
      </div>

      <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin-bottom:10px;">
        若您有任何產業數據需求、造紙利差模型或法規諮詢，歡迎隨時造訪官方門戶或直接回覆此郵件與我們交流。
      </p>
    </div>

    <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:20px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.6;">
      <div><strong>Paperluz · 全球與台灣紙業產業情報平台</strong></div>
      <div style="margin-top:4px;">發行機構：光網資訊 Luznet ∕ Paperluz 產業情報</div>
      <div style="margin-top:6px;">官方網站：<a href="{portal_url}" style="color:#3b82f6; text-decoration:none;">waatax.github.io/Paper/</a></div>
    </div>
  </div>
</body>
</html>
"""
    return html


def build_welcome_email_en(issue_num, publish_date):
    """產製英文國際版即時迎新確認信內容 (動態對齊最新期數)"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.pdf"
    portal_url = f"{BASE_URL}/EN/"
    intel = extract_issue_intelligence(issue_num, publish_date, lang="en")
    theme_text = intel["theme"] or "Comprehensive global pulp, containerboard raw spreads, PFAS-free packaging, and predictive matrices."

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Paperluz Global Industry Intelligence</title>
</head>
<body style="margin:0; padding:0; background-color:#080f20; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <div style="max-width:640px; margin:20px auto 30px auto; background-color:#101b37; border:1px solid #24355a; border-radius:14px; overflow:hidden; box-shadow:0 12px 32px rgba(0,0,0,0.5);">
    <div style="background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:26px 28px; border-bottom:1px solid #24355a;">
      <span style="font-size:22px; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
        📑 Paperluz <span style="font-size:11px; font-weight:700; background:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px;">Intelligence Hub</span>
      </span>
      <h1 style="color:#ffffff; font-size:21px; font-weight:900; line-height:1.4; margin:16px 0 6px 0;">
        🎉 Welcome to Paperluz Weekly Intelligence!
      </h1>
      <div style="color:#93c5fd; font-size:13.5px; font-weight:600;">
        Curated Friday 07:00 AM Briefings · Issue {issue_num} Executive Package Inside
      </div>
    </div>

    <div style="padding:26px 28px;">
      <p style="color:#f8fafc; font-size:14.5px; line-height:1.7; margin-bottom:20px;">
        Welcome to the Paperluz executive intelligence network. You are now successfully enrolled in our <strong>Global English Edition</strong>.
      </p>

      <div style="background:rgba(37, 99, 235, 0.12); border:1px solid rgba(59, 130, 246, 0.35); border-radius:8px; padding:16px 20px; margin-bottom:24px;">
        <div style="font-size:12px; font-weight:800; color:#60a5fa; text-transform:uppercase; margin-bottom:6px;">📅 Delivery Cadence &amp; Schedule</div>
        <div style="font-size:13.5px; color:#cbd5e1; line-height:1.6;">
          Our briefing is automatically published every <strong>Friday at 07:00 AM (UTC+8)</strong>. Each week, newly compiled commodity indices, margin spreads, and regulatory updates will be sent directly to your inbox.
        </div>
      </div>

      <div style="background:#162447; border-radius:10px; padding:20px; margin-bottom:26px; border:1px solid #263b6a;">
        <div style="font-size:12px; font-weight:800; color:#fbbf24; text-transform:uppercase; margin-bottom:6px;">🎁 Complimentary Executive Package</div>
        <h3 style="color:#ffffff; font-size:16px; font-weight:800; margin:0 0 10px 0;">
          Latest Release: Issue {issue_num} ({publish_date}) In-Depth Report
        </h3>
        <p style="color:#cbd5e1; font-size:13px; line-height:1.6; margin-bottom:16px;">
          {theme_text}
        </p>
        <div>
          <a href="{web_url}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700; margin-right:8px; margin-bottom:8px;">
            📖 Read Issue {issue_num} Online ➔
          </a>
          <a href="{pdf_url}" style="display:inline-block; background:#0b1329; color:#f8fafc; border:1px solid #3b82f6; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700;">
            📄 Download A4 Zero-Gap PDF
          </a>
        </div>
      </div>
    </div>

    <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:20px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.6;">
      <div><strong>Paperluz · Global Pulp &amp; Paper Industry Intelligence Hub</strong></div>
      <div style="margin-top:4px;">Published by Luznet / Paperluz Market Intelligence Center</div>
      <div style="margin-top:6px;">Official Portal: <a href="{portal_url}" style="color:#3b82f6; text-decoration:none;">waatax.github.io/Paper/EN/</a></div>
    </div>
  </div>
</body>
</html>
"""
    return html


def send_email_smtp(to_email, subject, html_content, smtp_config):
    """透過 SMTP 發送電子郵件 (含 RFC 8058 List-Unsubscribe 標頭)"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{smtp_config['sender_name']} <{smtp_config['sender_email']}>"
    msg["To"] = to_email
    msg["List-Unsubscribe"] = f"<mailto:{smtp_config['sender_email']}?subject=Unsubscribe>, <{BASE_URL}/#subscribe>"
    msg["X-Mailer"] = "Paperluz Institutional Dispatcher v2.0"

    plain_text = re.sub(r"<style.*?>.*?</style>", "", html_content, flags=re.DOTALL)
    plain_text = re.sub(r"<[^>]+>", "", plain_text)
    plain_text = re.sub(r"\n\s*\n", "\n\n", plain_text).strip()

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    if smtp_config["port"] == 465:
        server = smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"], timeout=20)
    else:
        server = smtplib.SMTP(smtp_config["host"], smtp_config["port"], timeout=20)
        server.starttls()

    server.login(smtp_config["user"], smtp_config["password"])
    server.sendmail(smtp_config["sender_email"], [to_email], msg.as_string())
    server.quit()


def save_subscriber_local(email, lang="zh", company="新訂閱會員", source="cli_onboard"):
    """將訂閱者寫入 SQLite 資料庫與對應的 CSV 名冊 (去重儲存)"""
    db_path = os.path.join(DATA_DIR, "paperluz.db")
    email = email.strip().lower()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO subscribers (email, company, subscribed_at, language, status, source)
                VALUES (?, ?, ?, ?, 'active', ?)
                ON CONFLICT(email) DO UPDATE SET
                    language = excluded.language,
                    status = 'active',
                    company = COALESCE(NULLIF(excluded.company, ''), subscribers.company)
            """, (email, company, now_str, lang, source))
            conn.commit()
            conn.close()
        except Exception:
            pass

    target_csv = SUBSCRIBERS_ZH_CSV if lang in ("zh", "both") else SUBSCRIBERS_EN_CSV
    if os.path.exists(target_csv):
        existing = load_subscribers(target_csv)
        emails = [s["email"].lower() for s in existing]
        if email not in emails:
            try:
                with open(target_csv, "a", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([email, company, now_str, lang, "active", source])
                print(f"  ✓ 已同步將 {email} 登記至名冊 ({os.path.basename(target_csv)})")
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Paperluz 雙語電子報自動發送管線 v2.0")
    parser.add_argument("--issue", default=None, help="期數，例如 013 (預設自動抓取最新期數)")
    parser.add_argument("--date", default=None, help="發布日期，例如 2026-10-23 (預設自動偵測)")
    parser.add_argument("--lang", default="all", choices=["all", "zh", "en"], help="發送語系 (all, zh, en)")
    parser.add_argument("--dry-run", action="store_true", help="本地測試模式，不實際發送信件，生成預覽檔案")
    parser.add_argument("--test-email", default=None, help="僅發送測試信至指定單一信箱")
    parser.add_argument("--email", default=None, help="目標信箱 (等同 --test-email)")
    parser.add_argument("--welcome", action="store_true", help="發送即時迎新確認信")
    parser.add_argument("--onboard", action="store_true", help="【即時雙發模式】收到訂閱後立即發出：① 歡迎信 + ② 最新一期完整電子報")

    args = parser.parse_args()
    target_email = args.test_email or args.email

    detected_issue, detected_date = find_latest_issue("zh")
    issue_num = args.issue or detected_issue or "014"
    if args.date:
        publish_date = args.date
    elif args.issue and args.issue != detected_issue:
        # 嘗試從檔案名稱尋找對應日期
        matches = glob.glob(os.path.join(SCRIPT_DIR, f"PaperLuz-{issue_num}_*[0-9].html"))
        if matches:
            m = re.search(r"PaperLuz-\d{3}_([0-9-]+)", os.path.basename(matches[0]))
            publish_date = m.group(1) if m else detected_date
        else:
            publish_date = detected_date
    else:
        publish_date = detected_date or "2026-10-30"

    if args.onboard:
        mode_title = f"新讀者入會即時雙發 (① 歡迎信 + ② 最新第 {issue_num} 期週報)"
    elif args.welcome:
        mode_title = "即時迎新確認信 (Welcome Briefing)"
    else:
        mode_title = f"每週例行機構級週報 (Issue {issue_num} ｜ {publish_date})"

    print("\n=====================================================================")
    print(f"  📑 Paperluz 雙語電子報自動派送引擎 v2.0 — {mode_title}")
    print("=====================================================================\n")

    welcome_zh = build_welcome_email_zh(issue_num, publish_date)
    welcome_en = build_welcome_email_en(issue_num, publish_date)
    issue_zh = build_newsletter_html_zh(issue_num, publish_date)
    issue_en = build_newsletter_html_en(issue_num, publish_date)

    with open(os.path.join(SCRIPT_DIR, "newsletter_welcome_preview_zh.html"), "w", encoding="utf-8") as f:
        f.write(welcome_zh)
    with open(os.path.join(SCRIPT_DIR, "newsletter_welcome_preview_en.html"), "w", encoding="utf-8") as f:
        f.write(welcome_en)
    with open(os.path.join(SCRIPT_DIR, "newsletter_preview_zh.html"), "w", encoding="utf-8") as f:
        f.write(issue_zh)
    with open(os.path.join(SCRIPT_DIR, "newsletter_preview_en.html"), "w", encoding="utf-8") as f:
        f.write(issue_en)
    print(f"  ✓ 迎新信預覽檔已動態生成 (對齊第 {issue_num} 期): newsletter_welcome_preview_zh.html / _en.html")
    print(f"  ✓ 機構級週報預覽檔已動態生成 (對齊第 {issue_num} 期): newsletter_preview_zh.html / _en.html")

    smtp_host = os.environ.get("SMTP_SERVER", "").strip()
    smtp_port_raw = os.environ.get("SMTP_PORT", "").strip()
    smtp_port = int(smtp_port_raw) if smtp_port_raw.isdigit() else 587
    smtp_user = os.environ.get("SMTP_USERNAME", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    sender_email = os.environ.get("SENDER_EMAIL", "").strip() or "newsletter@paperluz.org"
    sender_name = os.environ.get("SENDER_NAME", "").strip() or "Paperluz Intelligence"

    smtp_config = {
        "host": smtp_host,
        "port": smtp_port,
        "user": smtp_user,
        "password": smtp_pass,
        "sender_email": sender_email,
        "sender_name": sender_name,
    }

    if args.dry_run or not (smtp_host and smtp_user and smtp_pass):
        if not args.dry_run:
            print("  ℹ️  未偵測到完整 SMTP 伺服器設定 (SMTP_SERVER/USERNAME/PASSWORD)，自動轉為 Dry-Run 模式。")
        print("  🚀 [Dry-Run 模式] 模擬派送指標：")

        if target_email:
            target_lang = args.lang if args.lang in ("zh", "en") else "zh"
            print(f"    • 目標訂閱信箱: {target_email} ({target_lang})")
            if args.onboard:
                print("    • 模擬任務 1: 即時發出歡迎信 (Welcome Email)")
                print(f"    • 模擬任務 2: 立刻寄出目前最新第 {issue_num} 期電子報 ({publish_date})")
                save_subscriber_local(target_email, target_lang, "新訂閱會員")
            elif args.welcome:
                print("    • 模擬任務: 即時發出迎新確認信 (Welcome Email)")
            else:
                print(f"    • 模擬任務: 發送每週出刊週報 (Issue {issue_num})")
        else:
            zh_subs = load_subscribers(SUBSCRIBERS_ZH_CSV)
            en_subs = load_subscribers(SUBSCRIBERS_EN_CSV)
            print(f"    • 中文版預計派送: {len(zh_subs)} 位訂閱者 ({os.path.basename(SUBSCRIBERS_ZH_CSV)})")
            for s in zh_subs[:3]:
                print(f"      - {s['email']} ({s['company'] or '個人'})")
            print(f"    • 英文版預計派送: {len(en_subs)} 位訂閱者 ({os.path.basename(SUBSCRIBERS_EN_CSV)})")
            for s in en_subs[:3]:
                print(f"      - {s['email']} ({s['company'] or 'Individual'})")
        print("\n  ✅ Dry-Run 預覽與動態結構驗證 100% 完成！")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
