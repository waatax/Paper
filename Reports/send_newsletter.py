#!/usr/bin/env python3
"""
Paperluz 雙語電子報自動派送引擎 (Automated Weekly Newsletter Dispatcher)
========================================================================

功能：
  1. 讀取最新出刊或指定期數（HTML / 數據）內容。
  2. 自適應產製符合各大主流郵件客戶端（Apple Mail, Gmail, Outlook）的自適應響應式 HTML 郵件。
  3. 分流讀取中文訂閱名冊 (subscribers_zh.csv) 與英文訂閱名冊 (subscribers_en.csv)。
  4. 支援 SMTP 發送（Gmail, Resend, SendGrid, AWS SES 等標準 SMTP）。
  5. 支援 --dry-run 本地預覽產製，安全驗證郵件結構與排版。
  6. 支援 --test-email 指定單一收件人發送測試。

用法範例：
  # 本地 Dry-Run 預覽生成（不實際寄信）
  python Reports/send_newsletter.py --issue 008 --dry-run

  # 指定寄送測試信至個人信箱
  python Reports/send_newsletter.py --issue 008 --test-email myname@company.com --lang zh

  # 正式發送（中文名冊寄中文版，英文名冊寄英文版）
  python Reports/send_newsletter.py --issue 008
"""

import argparse
import csv
import glob
import os
import re
import smtplib
import sys
import time
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
        # Fallback to any PaperLuz html
        files = glob.glob(os.path.join(SCRIPT_DIR, "PaperLuz-*.html"))
    if not files:
        return None, None
    files.sort()
    latest_file = files[-1]
    # Extract issue number
    m = re.search(r"PaperLuz-(\d{3})_([0-9-]+)", os.path.basename(latest_file))
    if m:
        return m.group(1), m.group(2)
    return "009", "2026-09-25"


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


def build_newsletter_html_zh(issue_num, publish_date):
    """產製符合頂級電子報質感的繁體中文響應式 HTML 郵件內容"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.pdf"
    portal_url = f"{BASE_URL}/"

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Paperluz 產業情報週報 第 {issue_num} 期 ({publish_date})</title>
</head>
<body style="margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <div style="max-width:640px; margin:0 auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; margin-top:20px; margin-bottom:30px; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
    
    <!-- Top Brand Bar -->
    <div style="background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:24px 28px; border-bottom:1px solid #24355a;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <span style="font-size:22px; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
          📑 Paperluz <span style="font-size:11px; font-weight:700; background:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px;">Intelligence Hub</span>
        </span>
        <span style="font-size:12px; font-weight:600; color:#94a3b8; float:right;">第 {issue_num} 期 ｜ {publish_date}</span>
      </div>
      <div style="clear:both;"></div>
      <h1 style="color:#ffffff; font-size:20px; font-weight:800; line-height:1.4; margin:16px 0 6px 0;">
        全球與台灣紙業產業情報週報
      </h1>
      <div style="color:#60a5fa; font-size:13px; font-weight:600;">
        每週五準時晨間直送 · 原物料行情報告 · 獨家產業利差模型 · 法規警報
      </div>
    </div>

    <!-- Alert / Main Highlights -->
    <div style="padding:24px 28px;">
      <div style="background:rgba(239, 68, 68, 0.12); border-left:4px solid #ef4444; padding:12px 16px; border-radius:4px; margin-bottom:24px;">
        <div style="color:#ef4444; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">🚨 本週核心戰略焦點</div>
        <div style="color:#f8fafc; font-size:14px; font-weight:600; line-height:1.5;">
          歐盟 PFHxA 禁令最後 48 小時生效 × 美緬因州控告 Huhtamaki 與 Sappi 污染水源 × 台灣四大紙廠 9 月營收全員出爐與雙 11 二輪提價 × IP 啟動 DS Smith 歐洲業務分拆或 60 億美元出售雙軌評估 × 日本製紙無鋁無塑內側印刷紙盒問世
        </div>
      </div>

      <!-- Executive KPIs Table -->
      <h3 style="color:#ffffff; font-size:15px; font-weight:700; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:14px;">
        📊 關鍵核心行情指標 (Flash KPIs)
      </h3>
      <table style="width:100%; border-collapse:collapse; margin-bottom:24px; font-size:13px;">
        <thead>
          <tr style="background:#1a294f; color:#94a3b8; text-align:left;">
            <th style="padding:10px 12px; border-radius:6px 0 0 6px;">指標項目</th>
            <th style="padding:10px 12px;">最新報價</th>
            <th style="padding:10px 12px; border-radius:0 6px 6px 0;">走勢與利差解讀</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">布蘭特原油 (Brent)</td>
            <td style="padding:10px 12px; color:#22c55e; font-weight:800;">$74.45 / 桶</td>
            <td style="padding:10px 12px; color:#94a3b8;">週續跌 -6.0% · IEA 下調需求預期與地緣緩解</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">中國進口針葉漿 (NBSK)</td>
            <td style="padding:10px 12px; color:#60a5fa; font-weight:800;">USD 694 / 噸</td>
            <td style="padding:10px 12px; color:#94a3b8;">附註 RMB 4,935 · 北歐 UPM/Stora Enso 減產支撐</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">美國 11# OCC 廢紙</td>
            <td style="padding:10px 12px; color:#f59e0b; font-weight:800;">$135 / 美噸</td>
            <td style="padding:10px 12px; color:#94a3b8;">出口強韌 · 亞洲進口 CIF $178/噸</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">台灣四大紙廠 9月營收</td>
            <td style="padding:10px 12px; color:#a78bfa; font-weight:800;">永豐餘 66.5億</td>
            <td style="padding:10px 12px; color:#94a3b8;">正隆 41.8億 / 榮成 47.9億 / 華紙 15.2億全員出爐</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">北美工紙 Raw Spread</td>
            <td style="padding:10px 12px; color:#38bdf8; font-weight:800;">$840 / 短噸</td>
            <td style="padding:10px 12px; color:#94a3b8;">歷史極值 · IP 啟動 DS Smith 歐洲 60 億美元雙軌評估</td>
          </tr>
          <tr style="color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">歐盟 PFHxA 禁用條款</td>
            <td style="padding:10px 12px; color:#ef4444; font-weight:800;">倒數 2 天</td>
            <td style="padding:10px 12px; color:#94a3b8;">10/18 零時強制生效 · 美緬因州提告紙廠索賠</td>
          </tr>
        </tbody>
      </table>

      <!-- 5 Takeaways -->
      <h3 style="color:#ffffff; font-size:15px; font-weight:700; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:14px;">
        💡 本週 5 大決策洞察 (Executive Briefs)
      </h3>
      <ul style="color:#cbd5e1; font-size:13.5px; line-height:1.7; padding-left:18px; margin-bottom:28px;">
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">台灣四大紙廠 9 月營收全員出爐：永豐餘 66.5 億、榮成累賺 5.99 億、家紙雙雄承諾年底前衛生紙凍漲</strong>：永豐餘（1907）9 月營收 66.53 億元（YoY +3.95%，前 9 月 574.15 億元）；華紙（1905）9 月營收 15.20 億元；正隆（1904）41.78 億元（YoY +17.08%）；榮成（1909）47.90 億元（YoY +25.29%，前 9 月累計稅前淨利 5.99 億元、每股稅前盈餘 0.46 元）。永豐餘與正隆於 10/15 雙雙承諾消費品衛生紙年底前絕不漲價。
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">歐盟 PFHxA 禁令最後 48 小時強制生效 × 美緬因州控告 Huhtamaki、Sappi 與金百利克拉克污染水源</strong>：歐盟 Regulation (EU) 2024/2462 將於 2026 年 10 月 18 日零時正式生效；大西洋彼岸美國緬因州奧古斯塔公用事業局（GAUD）於 10/15 向聯邦法院正式起訴 Huhtamaki、Sappi North America 及 Kimberly-Clark，指控紙漿與防油紙模塑廠排放 PFAS 致河水超標，求償逾 200 萬美元過濾工程費。
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">國際紙業（IP）證實對歐洲包裝業務（原 DS Smith）啟動「倫敦上市或 60 億美元私募出售」雙軌評估</strong>：IP 為聚焦高毛利北美市場（Raw Spread 穩居 $840/短噸歷史極值），證實正推進 EMEA 業務倫敦分拆上市（預計 11/3 舉辦資本市場日），同時接獲 Lone Star 與 Atlas Holdings 高達 60 億美元之收購意向。
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">雙 11 電商旺季備貨點火：玖龍領漲中國箱板瓦楞紙第二輪 +50 元/噸，榮成與永豐餘全面跟進</strong>：隨雙 11 物流紙箱進入最後備貨衝刺，玖龍紙業領銜啟動 10 月中旬第二輪提價（每噸再漲 50 元），台灣榮成與永豐餘大陸廠區同步跟進，單月累計漲幅達 80–100 元/噸。
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">南美闊葉漿擴產與北歐長纖減產對決 × 日本製紙「無鋁無塑內側印刷紙盒」問世</strong>：Arauco 巴西 46 億美元 Sucuriú 項目進度達 81%，CMPC 則因 46 億美元擴產計畫面臨信評降級壓力；北歐 UPM Pietarsaari 漿廠 10 月停機減產、Stora Enso 關閉長纖線支撐 NBSK 報 USD 694/噸。日本製紙推出可併入牛奶盒回收體系之「Non-Aluminum Fuji-Pak」，澳洲超市巨頭 Coles 則調漲結帳紙袋 20% 至 30 澳分。
        </li>
      </ul>

      <!-- CTA Buttons -->
      <div style="text-align:center; padding:10px 0 20px 0;">
        <a href="{web_url}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:700; margin-right:10px; margin-bottom:10px; box-shadow:0 4px 14px rgba(37,99,235,0.4);">
          在線閱讀完整週報 (HTML) ➔
        </a>
        <a href="{pdf_url}" style="display:inline-block; background:#1e293b; color:#ffffff; border:1px solid #334155; text-decoration:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:700; margin-bottom:10px;">
          下載 A4 Zero-Gap PDF 交付檔
        </a>
      </div>

    </div>

    <!-- Email Footer -->
    <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:20px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.6;">
      <div><strong>Paperluz · 全球與台灣紙業產業情報平台</strong></div>
      <div style="margin-top:4px;">發行機構：光網資訊 Luznet ∕ Paperluz 產業情報中心</div>
      <div style="margin-top:6px;">官方網站：<a href="{portal_url}" style="color:#3b82f6; text-decoration:none;">waatax.github.io/Paper/</a> ｜ <a href="{portal_url}EN/" style="color:#3b82f6; text-decoration:none;">English Edition</a></div>
      <div style="margin-top:12px; border-top:1px solid #1a294f; padding-top:12px; color:#475569;">
        您收到此郵件是因為您在 Paperluz 官方門戶登記訂閱。若您不希望再收到每週出刊通知，請回覆信件主旨註明 Unsubscribe 或至官網退訂。
      </div>
    </div>

  </div>
</body>
</html>
"""
    return html


def build_newsletter_html_en(issue_num, publish_date):
    """產製符合頂級電子報質感的英文國際版響應式 HTML 郵件內容"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.pdf"
    portal_url = f"{BASE_URL}/EN/"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Paperluz Global Industry Intelligence Weekly Issue {issue_num} ({publish_date})</title>
</head>
<body style="margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <div style="max-width:640px; margin:0 auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; margin-top:20px; margin-bottom:30px; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
    
    <!-- Top Brand Bar -->
    <div style="background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:24px 28px; border-bottom:1px solid #24355a;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <span style="font-size:22px; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
          📑 Paperluz <span style="font-size:11px; font-weight:700; background:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px;">Intelligence Hub</span>
        </span>
        <span style="font-size:12px; font-weight:600; color:#94a3b8; float:right;">Issue {issue_num} ｜ {publish_date}</span>
      </div>
      <div style="clear:both;"></div>
      <h1 style="color:#ffffff; font-size:20px; font-weight:800; line-height:1.4; margin:16px 0 6px 0;">
        Global Pulp & Paper Industry Intelligence Briefing
      </h1>
      <div style="color:#60a5fa; font-size:13px; font-weight:600;">
        Curated Weekly Friday Intelligence · Commodity Spot Tracking · Mill Margins · Regulatory Radar
      </div>
    </div>

    <!-- Alert / Main Highlights -->
    <div style="padding:24px 28px;">
      <div style="background:rgba(239, 68, 68, 0.12); border-left:4px solid #ef4444; padding:12px 16px; border-radius:4px; margin-bottom:24px;">
        <div style="color:#ef4444; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">🚨 Strategic Executive Alert</div>
        <div style="color:#f8fafc; font-size:14px; font-weight:600; line-height:1.5;">
          EU PFHxA Ban Enters Final 48-Hour Countdown × Maine Utility Sues Huhtamaki & Sappi Over PFAS × Taiwan Big 4 Complete Sep Earnings & Double 11 Second Hike Wave × IP Evaluates $6B EMEA (DS Smith) Sale vs Spin-Off × Nippon Paper Debuts Non-Aluminum Fuji-Pak
        </div>
      </div>

      <!-- Executive KPIs Table -->
      <h3 style="color:#ffffff; font-size:15px; font-weight:700; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:14px;">
        📊 Key Market Indices & Benchmarks (Flash KPIs)
      </h3>
      <table style="width:100%; border-collapse:collapse; margin-bottom:24px; font-size:13px;">
        <thead>
          <tr style="background:#1a294f; color:#94a3b8; text-align:left;">
            <th style="padding:10px 12px; border-radius:6px 0 0 6px;">Commodity / Metric</th>
            <th style="padding:10px 12px;">Latest Spot Price</th>
            <th style="padding:10px 12px; border-radius:0 6px 6px 0;">Market Dynamics</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">Brent Crude Oil</td>
            <td style="padding:10px 12px; color:#22c55e; font-weight:800;">$74.45 / bbl</td>
            <td style="padding:10px 12px; color:#94a3b8;">-6.0% WoW pullback · IEA trims global oil demand outlook</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">China NBSK Import Spot</td>
            <td style="padding:10px 12px; color:#60a5fa; font-weight:800;">USD 694 / MT</td>
            <td style="padding:10px 12px; color:#94a3b8;">RMB 4,935 · Nordic UPM/Stora Enso curtailments tighten supply</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">US OCC #11 Export FAS</td>
            <td style="padding:10px 12px; color:#f59e0b; font-weight:800;">$135 / ST</td>
            <td style="padding:10px 12px; color:#94a3b8;">Resilient export pricing · Asia CIF steady at $178/MT</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">Taiwan Big 4 Sep Revenue</td>
            <td style="padding:10px 12px; color:#a78bfa; font-weight:800;">YFY NT$6.65B</td>
            <td style="padding:10px 12px; color:#94a3b8;">Cheng Loong 4.18B / Long Chen 4.79B / CHP 1.52B complete</td>
          </tr>
          <tr style="border-bottom:1px solid #1a294f; color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">US Containerboard Spread</td>
            <td style="padding:10px 12px; color:#38bdf8; font-weight:800;">$840 / ST</td>
            <td style="padding:10px 12px; color:#94a3b8;">Historic high · IP evaluates $6B EMEA (DS Smith) exit</td>
          </tr>
          <tr style="color:#f8fafc;">
            <td style="padding:10px 12px; font-weight:700;">EU PFHxA Ban Compliance</td>
            <td style="padding:10px 12px; color:#ef4444; font-weight:800;">2 Days Left</td>
            <td style="padding:10px 12px; color:#94a3b8;">Enforceable Oct 18 · Maine water utility files PFAS suit</td>
          </tr>
        </tbody>
      </table>

      <!-- 5 Takeaways -->
      <h3 style="color:#ffffff; font-size:15px; font-weight:700; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:14px;">
        💡 Executive Briefings & Market Intelligence (5 Key Insights)
      </h3>
      <ul style="color:#cbd5e1; font-size:13.5px; line-height:1.7; padding-left:18px; margin-bottom:28px;">
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">Taiwan Big 4 Complete Sep Revenue: YFY NT$6.65B, Long Chen 9M Profit NT$599M, Tissue Freeze Pledged</strong>: YFY (1907) posted Sep revenue of NT$6.653B (+3.95% YoY; 9M NT$57.415B); CHP (1905) recorded NT$1.520B; Cheng Loong (1904) reached NT$4.178B (+17.08% YoY); Long Chen (1909) delivered NT$4.790B (+25.29% YoY) with 9M cumulative pre-tax profit of NT$599M (pre-tax EPS NT$0.46). On Oct 15, YFY and Cheng Loong pledged a consumer tissue price freeze through year-end.
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">EU PFHxA Ban Final 48-Hour Countdown × Maine Utility Sues Huhtamaki, Sappi & Kimberly-Clark Over PFAS</strong>: EU Regulation (EU) 2024/2462 restricting PFHxA takes full legal effect at 00:00 on October 18, 2026. Simultaneously in the US, Maine's Greater Augusta Utility District filed a federal lawsuit on Oct 15 against Huhtamaki, Sappi North America, and Kimberly-Clark, alleging Kennebec River PFAS contamination (23.3 ppt vs 20 ppt limit) and seeking >$2M in filtration damages.
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">International Paper (IP) Evaluates Dual-Track Spin-Off or $6B Private Equity Sale for EMEA Packaging (DS Smith)</strong>: To sharpen its focus on high-margin North American operations ($840/ST Raw Spread peak), IP confirmed it is advancing a London listing for its EMEA business (Nov 3 Capital Markets Day) while entertaining ~$6B buyout bids from Lone Star and Atlas Holdings.
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">Double 11 Box Restocking Ignites Second October Containerboard Hike Wave (+RMB 50/MT)</strong>: Led by Nine Dragons' mid-October announcement of a second +RMB 50/MT hike across major Chinese bases, Taiwan's Long Chen and YFY followed suit across their mainland mills, bringing cumulative October increases to RMB 80–100/MT.
        </li>
        <li style="margin-bottom:8px;">
          <strong style="color:#ffffff;">South American Megaprojects vs Nordic Curtailments × Nippon Paper Debuts "Non-Aluminum Fuji-Pak"</strong>: Arauco's $4.6B Sucuriú mill in Brazil reached 81% completion while CMPC faces credit-rating pressure over its $4.6B Natureza project; Nordic curtailments at UPM Pietarsaari and Stora Enso Skutskär supported NBSK at USD 694/MT. In food packaging, Nippon Paper commercialized its recyclable "Non-Aluminum Fuji-Pak" with Ito En, while Australian grocer Coles hiked checkout paper bag prices by 20% to 30c.
        </li>
      </ul>

      <!-- CTA Buttons -->
      <div style="text-align:center; padding:10px 0 20px 0;">
        <a href="{web_url}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:700; margin-right:10px; margin-bottom:10px; box-shadow:0 4px 14px rgba(37,99,235,0.4);">
          Read Full Report Online (HTML) ➔
        </a>
        <a href="{pdf_url}" style="display:inline-block; background:#1e293b; color:#ffffff; border:1px solid #334155; text-decoration:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:700; margin-bottom:10px;">
          Download A4 Zero-Gap PDF Deliverable
        </a>
      </div>

    </div>

    <!-- Email Footer -->
    <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:20px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.6;">
      <div><strong>Paperluz · Global Pulp & Paper Industry Intelligence Hub</strong></div>
      <div style="margin-top:4px;">Published by Luznet / Paperluz Market Intelligence Center</div>
      <div style="margin-top:6px;">Official Portal: <a href="{portal_url}" style="color:#3b82f6; text-decoration:none;">waatax.github.io/Paper/EN/</a> ｜ <a href="{BASE_URL}/" style="color:#3b82f6; text-decoration:none;">繁體中文版</a></div>
      <div style="margin-top:12px; border-top:1px solid #1a294f; padding-top:12px; color:#475569;">
        You received this briefing because you are subscribed to the Paperluz executive distribution list. To manage your subscription or unsubscribe, please reply with "Unsubscribe" or visit our portal.
      </div>
    </div>

  </div>
</body>
</html>
"""
    return html


def build_welcome_email_zh(issue_num, publish_date):
    """產製繁體中文即時迎新確認信內容"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}.pdf"
    portal_url = f"{BASE_URL}/"

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>歡迎訂閱 Paperluz 全球與台灣紙業產業情報週報</title>
</head>
<body style="margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <div style="max-width:640px; margin:0 auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; margin-top:20px; margin-bottom:30px; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
    
    <div style="background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:26px 28px; border-bottom:1px solid #24355a;">
      <span style="font-size:22px; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
        📑 Paperluz <span style="font-size:11px; font-weight:700; background:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px;">Intelligence Hub</span>
      </span>
      <h1 style="color:#ffffff; font-size:21px; font-weight:900; line-height:1.4; margin:16px 0 6px 0;">
        🎉 感謝您訂閱 Paperluz 每週產業情報！
      </h1>
      <div style="color:#60a5fa; font-size:13.5px; font-weight:600;">
        每週五晨間 07:00 準時發送 · 您的專屬迎新禮包已備妥
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

      <div style="background:#1a294f; border-radius:10px; padding:20px; margin-bottom:26px; border:1px solid #24355a;">
        <div style="font-size:12px; font-weight:800; color:#f59e0b; text-transform:uppercase; margin-bottom:6px;">🎁 迎新專屬資料禮包</div>
        <h3 style="color:#ffffff; font-size:16px; font-weight:800; margin:0 0 10px 0;">
          最新出刊：第 {issue_num} 期 ({publish_date}) 深度專題完整版
        </h3>
        <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin-bottom:16px;">
          包含最新布蘭特原油 $74.45/桶、中國進口針葉漿 NBSK USD 694/噸、台灣四大紙廠 9 月營收全員出爐與雙 11 二輪提價、IP 歐洲業務 60 億美元雙軌評估，以及歐盟 PFHxA 禁用新規最後 48 小時生效與美緬因州 PFAS 水源訴訟。
        </p>
        <div>
          <a href="{web_url}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700; margin-right:8px; margin-bottom:8px;">
            在線閱讀第 {issue_num} 期 ➔
          </a>
          <a href="{pdf_url}" style="display:inline-block; background:#0b1329; color:#f8fafc; border:1px solid #334155; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700;">
            下載 A4 Zero-Gap PDF
          </a>
        </div>
      </div>

      <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin-bottom:10px;">
        若您有任何產業數據需求、造紙利差模型或法規諮詢，歡迎隨時造訪官方門戶或直接回覆此郵件與我們交流。
      </p>
    </div>

    <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:20px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.6;">
      <div><strong>Paperluz · 全球與台灣紙業產業情報平台</strong></div>
      <div style="margin-top:4px;">發行機構：光網資訊 Luznet ∕ Paperluz 產業情報中心</div>
      <div style="margin-top:6px;">官方網站：<a href="{portal_url}" style="color:#3b82f6; text-decoration:none;">waatax.github.io/Paper/</a></div>
      <div style="margin-top:12px; border-top:1px solid #1a294f; padding-top:12px; color:#475569;">
        若您不希望再收到每週出刊通知，請回覆信件主旨註明 Unsubscribe 或至官網隨時取消訂閱。
      </div>
    </div>

  </div>
</body>
</html>
"""
    return html


def build_welcome_email_en(issue_num, publish_date):
    """產製英文國際版即時迎新確認信內容"""
    web_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.html"
    pdf_url = f"{BASE_URL}/Reports/PaperLuz-{issue_num}_{publish_date}_EN.pdf"
    portal_url = f"{BASE_URL}/EN/"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Paperluz Global Industry Intelligence</title>
</head>
<body style="margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <div style="max-width:640px; margin:0 auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; margin-top:20px; margin-bottom:30px; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
    
    <div style="background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:26px 28px; border-bottom:1px solid #24355a;">
      <span style="font-size:22px; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
        📑 Paperluz <span style="font-size:11px; font-weight:700; background:#2563eb; color:#ffffff; padding:3px 8px; border-radius:4px; text-transform:uppercase; margin-left:6px;">Intelligence Hub</span>
      </span>
      <h1 style="color:#ffffff; font-size:21px; font-weight:900; line-height:1.4; margin:16px 0 6px 0;">
        🎉 Welcome to Paperluz Weekly Intelligence!
      </h1>
      <div style="color:#60a5fa; font-size:13.5px; font-weight:600;">
        Curated Friday 07:00 AM Briefings · Your Welcome Gift Inside
      </div>
    </div>

    <div style="padding:26px 28px;">
      <p style="color:#f8fafc; font-size:14.5px; line-height:1.7; margin-bottom:20px;">
        Welcome to the Paperluz executive intelligence network. You are now successfully enrolled in our <strong>Global English Edition</strong>.
      </p>

      <div style="background:rgba(37, 99, 235, 0.12); border:1px solid rgba(59, 130, 246, 0.35); border-radius:8px; padding:16px 20px; margin-bottom:24px;">
        <div style="font-size:12px; font-weight:800; color:#60a5fa; text-transform:uppercase; margin-bottom:6px;">📅 Delivery Cadence & Schedule</div>
        <div style="font-size:13.5px; color:#cbd5e1; line-height:1.6;">
          Our briefing is automatically published every <strong>Friday at 07:00 AM (UTC+8)</strong>. Each week, newly compiled commodity indices, margin spreads, and regulatory updates will be sent directly to your inbox.
        </div>
      </div>

      <div style="background:#1a294f; border-radius:10px; padding:20px; margin-bottom:26px; border:1px solid #24355a;">
        <div style="font-size:12px; font-weight:800; color:#f59e0b; text-transform:uppercase; margin-bottom:6px;">🎁 Complimentary Executive Package</div>
        <h3 style="color:#ffffff; font-size:16px; font-weight:800; margin:0 0 10px 0;">
          Latest Release: Issue {issue_num} ({publish_date}) In-Depth Report
        </h3>
        <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin-bottom:16px;">
          Covering Brent crude at $74.45/bbl, China NBSK import spot at USD 694/MT, Taiwan Big 4 complete September revenues & Double 11 second containerboard hike wave, IP's $6B EMEA (DS Smith) dual-track exit, and the final 48-hour EU PFHxA ban countdown alongside Maine's federal PFAS water utility lawsuit.
        </p>
        <div>
          <a href="{web_url}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700; margin-right:8px; margin-bottom:8px;">
            Read Issue {issue_num} Online ➔
          </a>
          <a href="{pdf_url}" style="display:inline-block; background:#0b1329; color:#f8fafc; border:1px solid #334155; text-decoration:none; padding:10px 18px; border-radius:6px; font-size:13px; font-weight:700;">
            Download A4 Zero-Gap PDF
          </a>
        </div>
      </div>
    </div>

    <div style="background-color:#0b1329; border-top:1px solid #24355a; padding:20px 28px; text-align:center; color:#64748b; font-size:12px; line-height:1.6;">
      <div><strong>Paperluz · Global Pulp & Paper Industry Intelligence Hub</strong></div>
      <div style="margin-top:4px;">Published by Luznet / Paperluz Market Intelligence Center</div>
      <div style="margin-top:6px;">Official Portal: <a href="{portal_url}" style="color:#3b82f6; text-decoration:none;">waatax.github.io/Paper/EN/</a></div>
    </div>

  </div>
</body>
</html>
"""
    return html


def send_email_smtp(to_email, subject, html_content, smtp_config):
    """透過 SMTP 發送電子郵件"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{smtp_config['sender_name']} <{smtp_config['sender_email']}>"
    msg["To"] = to_email

    # Plain text version
    plain_text = re.sub(r"<[^>]+>", "", html_content)
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
    
    # 1. 寫入 SQLite
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
        except Exception as e:
            pass

    # 2. 寫入 CSV
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
            except Exception as e:
                pass


def main():
    parser = argparse.ArgumentParser(description="Paperluz 電子報自動發送管線")
    parser.add_argument("--issue", default=None, help="期數，例如 008 (預設自動抓取最新期數)")
    parser.add_argument("--date", default=None, help="發布日期，例如 2026-09-18 (預設自動推估)")
    parser.add_argument("--lang", default="all", choices=["all", "zh", "en"], help="發送語系 (all, zh, en)")
    parser.add_argument("--dry-run", action="store_true", help="本地測試模式，不實際發送信件，生成預覽檔案")
    parser.add_argument("--test-email", default=None, help="僅發送測試信至指定單一信箱")
    parser.add_argument("--email", default=None, help="目標信箱 (等同 --test-email)")
    parser.add_argument("--welcome", action="store_true", help="發送即時迎新確認信")
    parser.add_argument("--onboard", action="store_true", help="【即時雙發模式】收到訂閱後立即發出：① 歡迎信 + ② 最新一期完整電子報")

    args = parser.parse_args()
    target_email = args.test_email or args.email

    # 自動識別期數與日期
    detected_issue, detected_date = find_latest_issue("zh")
    issue_num = args.issue or detected_issue or "009"
    publish_date = args.date or detected_date or "2026-09-25"

    if args.onboard:
        mode_title = "新讀者入會即時雙發 (① 歡迎信 + ② 最新一期週報)"
    elif args.welcome:
        mode_title = "即時迎新確認信 (Welcome Briefing)"
    else:
        mode_title = f"每週例行週報 (Issue {issue_num} ｜ {publish_date})"

    print(f"\n=======================================================")
    print(f"  📑 Paperluz 電子報自動發送管線 — {mode_title}")
    print(f"=======================================================\n")

    welcome_zh = build_welcome_email_zh(issue_num, publish_date)
    welcome_en = build_welcome_email_en(issue_num, publish_date)
    issue_zh = build_newsletter_html_zh(issue_num, publish_date)
    issue_en = build_newsletter_html_en(issue_num, publish_date)

    # 產製本地預覽檔
    with open(os.path.join(SCRIPT_DIR, "newsletter_welcome_preview_zh.html"), "w", encoding="utf-8") as f:
        f.write(welcome_zh)
    with open(os.path.join(SCRIPT_DIR, "newsletter_welcome_preview_en.html"), "w", encoding="utf-8") as f:
        f.write(welcome_en)
    with open(os.path.join(SCRIPT_DIR, "newsletter_preview_zh.html"), "w", encoding="utf-8") as f:
        f.write(issue_zh)
    with open(os.path.join(SCRIPT_DIR, "newsletter_preview_en.html"), "w", encoding="utf-8") as f:
        f.write(issue_en)
    print(f"  ✓ 迎新信預覽檔已生成: newsletter_welcome_preview_zh.html / _en.html")
    print(f"  ✓ 週報預覽檔已生成: newsletter_preview_zh.html / _en.html")

    # 檢查 SMTP 環境變數
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
            print(f"  ℹ️  未偵測到完整 SMTP 伺服器設定 (SMTP_SERVER/USERNAME/PASSWORD)，自動轉為 Dry-Run 模式。")
        print(f"  🚀 [Dry-Run 模式] 模擬派送指標：")
        
        if target_email:
            target_lang = args.lang if args.lang in ("zh", "en") else "zh"
            print(f"    • 目標訂閱信箱: {target_email} ({target_lang})")
            if args.onboard:
                print(f"    • 模擬任務 1: 即時發出歡迎信 (Welcome Email)")
                print(f"    • 模擬任務 2: 立刻寄出目前最新第 {issue_num} 期電子報 ({publish_date})")
                save_subscriber_local(target_email, target_lang, "新訂閱會員")
            elif args.welcome:
                print(f"    • 模擬任務: 即時發出迎新確認信 (Welcome Email)")
            else:
                print(f"    • 模擬任務: 發送每週出刊週報 (Issue {issue_num})")
        else:
            zh_subs = load_subscribers(SUBSCRIBERS_ZH_CSV)
            en_subs = load_subscribers(SUBSCRIBERS_EN_CSV)
            print(f"    • 中文版預計派送: {len(zh_subs)} 位訂閱者 ({os.path.basename(SUBSCRIBERS_ZH_CSV)})")
            for s in zh_subs[:3]:
                print(f"      - {s['email']} ({s['company'] or '個人'})")
            if len(zh_subs) > 3:
                print(f"      ... (其餘 {len(zh_subs)-3} 位)")

            print(f"    • 英文版預計派送: {len(en_subs)} 位訂閱者 ({os.path.basename(SUBSCRIBERS_EN_CSV)})")
            for s in en_subs[:3]:
                print(f"      - {s['email']} ({s['company'] or 'Individual'})")
            if len(en_subs) > 3:
                print(f"      ... (其餘 {len(en_subs)-3} 位)")

        print(f"\n  ✓ 預覽驗證成功！可直接在瀏覽器開啟預覽 HTML 確認排版樣式。")
        return 0

    # 正式發送流程
    if target_email:
        test_lang = args.lang if args.lang in ("zh", "en") else "zh"
        
        if args.onboard:
            # 收到訂閱後立即雙發：① 歡迎信 + ② 最新一期電子報
            subj_welcome = "🎉 歡迎加入 Paperluz 全球紙業情報網絡（訂閱確認與權益指南）" if test_lang == "zh" else "🎉 Welcome to Paperluz Intelligence Network (Subscription & Member Guide)"
            body_welcome = welcome_zh if test_lang == "zh" else welcome_en

            subj_issue = f"📑【最新出刊】Paperluz 紙業情報週報 第 {issue_num} 期 ({publish_date})" if test_lang == "zh" else f"📑 [Latest Issue] Paperluz Weekly Industry Intelligence Issue {issue_num} ({publish_date})"
            body_issue = issue_zh if test_lang == "zh" else issue_en

            print(f"  📤 [1/2] 正在即時發出歡迎信至 {target_email} ({test_lang})...")
            try:
                send_email_smtp(target_email, subj_welcome, body_welcome, smtp_config)
                print(f"    ✓ 歡迎信發送成功！")
            except Exception as e:
                print(f"    ✗ 歡迎信發送失敗: {e}")
                return 1

            time.sleep(1.0)
            print(f"  📤 [2/2] 正在立刻寄出最新第 {issue_num} 期電子報至 {target_email}...")
            try:
                send_email_smtp(target_email, subj_issue, body_issue, smtp_config)
                print(f"    ✓ 最新電子報發送成功！")
            except Exception as e:
                print(f"    ✗ 最新電子報發送失敗: {e}")
                return 1

            save_subscriber_local(target_email, test_lang, "新訂閱會員")
            print(f"\n  🎉 新訂閱戶雙發任務圓滿完成！")
            return 0

        elif args.welcome:
            subject = "🎉 感謝訂閱 Paperluz 全球紙業情報！這是您的迎新專屬資料包" if test_lang == "zh" else "🎉 Welcome to Paperluz Weekly Intelligence! Your Welcome Package"
            content = welcome_zh if test_lang == "zh" else welcome_en
            print(f"  📤 正在發送迎新信至 {target_email} ({test_lang})...")
            try:
                send_email_smtp(target_email, subject, content, smtp_config)
                print(f"  ✓ 迎新信發送成功！")
            except Exception as e:
                print(f"  ✗ 迎新信發送失敗: {e}")
                return 1
            return 0

        else:
            subject = f"【測試】Paperluz 週報 第 {issue_num} 期 ({publish_date})" if test_lang == "zh" else f"[Test] Paperluz Weekly Issue {issue_num} ({publish_date})"
            content = issue_zh if test_lang == "zh" else issue_en
            print(f"  📤 正在發送週報測試信至 {target_email} ({test_lang})...")
            try:
                send_email_smtp(target_email, subject, content, smtp_config)
                print(f"  ✓ 週報測試信發送成功！")
            except Exception as e:
                print(f"  ✗ 週報測試信發送失敗: {e}")
                return 1
            return 0

    # 批次分流發送
    print(f"  🚀 啟動正式批次派送程序...")
    sent_count = 0
    fail_count = 0

    if args.lang in ("all", "zh"):
        zh_subs = load_subscribers(SUBSCRIBERS_ZH_CSV)
        zh_subject = f"Paperluz 紙業產業情報週報 第 {issue_num} 期 ｜ {publish_date}"
        print(f"  • 開始派送中文版名冊 ({len(zh_subs)} 位)...")
        for s in zh_subs:
            try:
                send_email_smtp(s["email"], zh_subject, issue_zh, smtp_config)
                sent_count += 1
                print(f"    ✓ 已送達: {s['email']}")
                time.sleep(0.3)
            except Exception as e:
                fail_count += 1
                print(f"    ✗ 失敗: {s['email']} ({e})")

    if args.lang in ("all", "en"):
        en_subs = load_subscribers(SUBSCRIBERS_EN_CSV)
        en_subject = f"Paperluz Global Industry Intelligence Weekly Issue {issue_num} ｜ {publish_date}"
        print(f"  • 開始派送英文版名冊 ({len(en_subs)} 位)...")
        for s in en_subs:
            try:
                send_email_smtp(s["email"], en_subject, issue_en, smtp_config)
                sent_count += 1
                print(f"    ✓ 已送達: {s['email']}")
                time.sleep(0.3)
            except Exception as e:
                fail_count += 1
                print(f"    ✗ 失敗: {s['email']} ({e})")

    print(f"\n  🎉 派送任務結束：成功 {sent_count} 封 ｜ 失敗 {fail_count} 封")
    return 0


if __name__ == "__main__":
    sys.exit(main())
