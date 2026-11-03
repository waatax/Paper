#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paperluz Intelligence Engine v6.0 (Institutional Multi-Tier Gate & Deduplication Edition)
=========================================================================================
核心升級特點：
  1. 確定性時效閘門 (Deterministic Date Freshness Gate)：解析 RFC-2822 / ISO-8601 時間戳，嚴格剔除超過 N 天之過期舊聞 (解決 Yahoo Finance 歷史舊聞混入問題)。
  2. 多語反噪音與語境消歧閘門 (Multi-Lingual Anti-Noise & Context Disambiguation Gate)：
     - 攔截遊戲卡牌 (TCG 補充包「ザ・パック」偽陽性)、量化機器人股評 (Motley Fool / MarketBeat / Barchart)、SEO 假研報 (IndexBox / Future Market Insights) 與生活旅遊軟文。
     - 針對高歧義詞彙（「紙杯」、「紙袋」、「ザ・パック」）強制要求產業鏈共現語境 (Co-occurrence Context)。
  3. 情報源權威分級 (Source Authority Tiering - Tier 1 / Tier 2 / Tier 3)：
     - 自動識別媒體機構，賦予 Packaging Dive, Reuters, Lesprom, 日經, 日刊工業新聞, 工商時報, 經濟日報, 紙業網 等甲級權威源加權，並對內容農場降權。
  4. 語義事件聚類與近重複去重 (Event Clustering & Near-Duplicate Deduplication)：
     - 基於 Token / 雙字元 (Bigram) Jaccard 相似度演算法，自動合併同一事件的多家媒體轉載，保留最高權威主報導並標註「多源交叉印證數 (Corroboration Count)」。
  5. 供應鏈環節映射與決策信號分類 (Supply Chain Stage & Actionable Signal Tagging)：
     - 自動歸類至「🌲 上游木片與林業」、「🧪 中游木漿與廢紙」、「🏭 原紙與箱板紙廠」、「🍱 下游紙器與食品包裝」、「⚖️ 綠色法規與ESG」。
  6. SQLite 資料庫無縫聯動 (Automated DB Sync)：
     - 支援將高價值情報自動寫入 `Reports/data/paperluz.db` (`industry_news` 與 `pipeline_logs`)，打通週報產製管線。
"""

import sys
import os
import re
import html
import hashlib
import argparse
import urllib.request
import json
import sqlite3
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows 終端機預設 cp950 無法顯示 Unicode 符號，強制切換為 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(SCRIPT_DIR, "Reports", "data", "news_snapshots")
DB_PATH = os.path.join(SCRIPT_DIR, "Reports", "data", "paperluz.db")

# ═════════════════════════════════════════════════════════════════════════
# 1. 全球與區域情報來源註冊表 (28+ 精準高訊噪比 Feed 源)
# ═════════════════════════════════════════════════════════════════════════

REGIONAL_FEEDS = {
    "🇺🇸 北美造紙與包裝巨頭 (US Paper & Packaging: IP / Smurfit Westrock / PCA)": {
        "Google News (US Containerboard & Packaging)": "https://news.google.com/rss/search?q=containerboard+OR+kraftliner+OR+%22International+Paper%22+OR+%22Smurfit+Westrock%22+OR+%22Packaging+Corp%22+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Yahoo Finance (International Paper - IP)": "https://finance.yahoo.com/rss/headline?s=IP",
        "Yahoo Finance (Smurfit Westrock - SW)": "https://finance.yahoo.com/rss/headline?s=SW",
        "Yahoo Finance (Packaging Corp of America - PKG)": "https://finance.yahoo.com/rss/headline?s=PKG",
    },
    "🇺🇸 北美食品包裝與速食連鎖紙袋容器 (US Food Packaging: Paper Bags / Cups / Molded Fiber)": {
        "Google News (US Food Packaging & Paper Bags)": "https://news.google.com/rss/search?q=(%22paper+bag%22+OR+%22paper+cup%22+OR+%22molded+fiber%22+OR+%22PFAS-free%22)+(packaging+OR+paperboard)+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Google News (US Packaging Giants: Graphic Packaging / Novolex / Huhtamaki)": "https://news.google.com/rss/search?q=%22Graphic+Packaging%22+OR+%22Novolex%22+OR+%22Huhtamaki%22+OR+%22Pactiv+Evergreen%22+when:14d&hl=en-US&gl=US&ceid=US:en",
    },
    "🇪🇺 歐洲紙業與生物材料龍頭 (Europe Leaders: UPM / Stora Enso / Mondi / PPWR)": {
        "Google News (Europe Pulp & Biochemicals: UPM / Stora Enso / Mondi)": "https://news.google.com/rss/search?q=UPM-Kymmene+OR+%22Stora+Enso%22+OR+%22Mondi+Group%22+OR+%22Metsa+Board%22+OR+Billerud+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Google News (EU Packaging Regulations: PPWR / EUDR / PFHxA)": "https://news.google.com/rss/search?q=(PPWR+OR+EUDR+OR+PFHxA)+(packaging+OR+pulp+OR+paper)+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Yahoo Finance (UPM-Kymmene - UPMKY)": "https://finance.yahoo.com/rss/headline?s=UPMKY",
        "Yahoo Finance (Stora Enso - SEOAY)": "https://finance.yahoo.com/rss/headline?s=SEOAY",
    },
    "🇨🇱/🇧🇷 南美主要漿廠 (South America Pulp Giants: Arauco Chile / CMPC / Suzano)": {
        "Google News (Arauco Chile & CMPC & Suzano Pulp)": "https://news.google.com/rss/search?q=(%22Arauco%22+OR+%22CMPC%22+OR+%22Suzano%22+OR+%22Eldorado+Brasil%22)+pulp+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Yahoo Finance (Suzano - SUZ)": "https://finance.yahoo.com/rss/headline?s=SUZ",
        "Yahoo Finance (Empresas CMPC - CMPC.SN)": "https://finance.yahoo.com/rss/headline?s=CMPC.SN",
        "Yahoo Finance (Empresas Copec / Arauco - COPEC.SN)": "https://finance.yahoo.com/rss/headline?s=COPEC.SN",
    },
    "🪵 全球木片、廢紙與纖維原料鏈 (Woodchips, OCC & Global Fiber)": {
        "Google News (Global Woodchips & Pulpwood Trade)": "https://news.google.com/rss/search?q=(%22wood+chips%22+OR+woodchips+OR+pulpwood+OR+%22recovered+paper%22+OR+NBSK+OR+BHKP)+(pulp+OR+paper+OR+mill+OR+export)+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Google News (亞洲木片 紙漿 長纖 短纖 美廢 OCC)": "https://news.google.com/rss/search?q=(%E6%9C%A8%E7%89%87+OR+%E9%97%8A%E8%91%89%E6%BC%BF+OR+%E9%87%9D%E8%91%89%E6%BC%BF+OR+%E7%B4%99%E6%BC%BF+OR+%E5%BB%A2%E7%B4%99)+(%E9%80%A0%E7%B4%99+OR+%E6%BC%BF%E5%BB%A0+OR+%E5%A0%B1%E5%83%B9+OR+%E5%BA%AB%E5%AD%98)+when:14d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
    "🇯🇵 日本市場三大龍頭 (Japan Big 3: Oji / Daio / Nippon Paper)": {
        "Google News (日本紙業: 王子 大王 日本製紙 北越)": "https://news.google.com/rss/search?q=%E7%8E%8B%E5%AD%90%E3%83%9B%E3%83%BC%E3%83%AB%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E3%82%B9+OR+%E5%A4%A7%E7%8E%8B%E8%A3%BD%E7%B4%99+OR+%E6%97%A5%E6%9C%AC%E8%A3%BD%E7%B4%99+OR+%E5%8C%97%E8%B6%8A%E3%82%B3%E3%83%BC%E3%83%9D%E3%83%AC%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3+when:14d&hl=ja&gl=JP&ceid=JP:ja",
        "Yahoo Finance JP (王子ホールディングス - 3861.T)": "https://finance.yahoo.com/rss/headline?s=3861.T",
        "Yahoo Finance JP (大王製紙 - 3880.T)": "https://finance.yahoo.com/rss/headline?s=3880.T",
        "Yahoo Finance JP (日本製紙 - 3863.T)": "https://finance.yahoo.com/rss/headline?s=3863.T",
    },
    "🇯🇵 日本高階紙袋與脫塑食品容器 (Japan Sustainable Food Packaging & Paper Bags)": {
        "Google News (日本脫塑食品容器與紙製包材)": "https://news.google.com/rss/search?q=(%E7%B4%99%E8%A2%8B+OR+%E7%B4%99%E5%AE%B9%E5%99%A8+OR+%E3%83%91%E3%83%AB%E3%83%97%E3%83%A2%E3%83%BC%E3%83%AB%E3%83%89+OR+%E7%B4%99%E3%83%91%E3%83%83%E3%82%AF)+(%E8%84%B1%E3%83%97%E3%83%A9+OR+%E5%8C%85%E8%A3%85+OR+%E8%80%90%E6%B2%B9+OR+%E3%83%90%E3%83%AA%E3%82%A2)+when:14d&hl=ja&gl=JP&ceid=JP:ja",
        "Google News (日本包裝袋企業: ザ・パック シモジマ SHIELDPLUS)": "https://news.google.com/rss/search?q=(%22%E3%82%B6%E3%83%BB%E3%83%91%E3%83%83%E3%82%AF%22+OR+%E3%82%B7%E3%83%A2%E3%82%B8%E3%83%9E+OR+SHIELDPLUS)+(%E5%8C%85%E8%A3%85+OR+%E7%B4%99+OR+%E3%83%91%E3%83%83%E3%82%B1%E3%83%BC%E3%82%B8)+when:14d&hl=ja&gl=JP&ceid=JP:ja",
    },
    "🇨🇳 中國工紙、APP 金光 ∕ 博匯紙業 & 大宗白卡": {
        "Google News (中國紙業: 玖龍 山鷹 太陽 博匯 金光 白卡紙)": "https://news.google.com/rss/search?q=%E7%8E%96%E9%BE%99%E7%BA%B8%E4%B8%9A+OR+%E5%B1%B1%E9%B9%B0%E5%9B%BD%E9%99%85+OR+%E5%8D%9A%E6%B1%87%E7%BA%B8%E4%B8%9A+OR+%E5%A4%AA%E9%98%B3%E7%BA%B8%E4%B8%9A+OR+%E7%99%BD%E5%8D%A1%E7%BA%B8+OR+%E7%93%A6%E6%A5%9E%E7%BA%B8+when:14d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "Yahoo Finance CN (博匯紙業 - 600966.SS)": "https://finance.yahoo.com/rss/headline?s=600966.SS",
    },
    "🇨🇳 中國餐飲包裝與紙模塑出海 (China Food Contact & Molded Fiber: 白卡/紙杯/外賣紙袋)": {
        "Google News (中國紙模塑與植纖餐盒)": "https://news.google.com/rss/search?q=(%E7%BA%B8%E6%A8%A1%E5%A1%91+OR+%E6%A4%8D%E7%BA%A4%E9%A4%90%E7%9B%92+OR+%E7%BA%B8%E6%B5%86%E6%A8%A1%E5%A1%91+OR+%E4%BC%97%E9%91%AB%E8%82%A1%E4%BB%BD+OR+%E8%A3%95%E5%90%8C%E7%A7%91%E6%8A%80)+when:14d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "Google News (中國食品包裝紙與紙容器企業)": "https://news.google.com/rss/search?q=(%E9%A3%9F%E5%93%81%E5%8C%85%E8%A3%85%E7%BA%B8+OR+%E9%A3%9F%E5%93%81%E5%8D%A1%E7%BA%B8+OR+%E6%97%A0%E6%B0%9F%E9%98%B2%E6%B2%B9%E7%BA%B8+OR+%E6%B0%B4%E6%80%A7%E6%B6%82%E5%B1%82+%E7%BA%B8%E6%9D%AF)+when:14d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    },
    "🇦🇺/🇳🇿 澳洲與紐西蘭包裝轉型與植纖紙袋 (ANZ Packaging: APCO / Plastic Bans / Molded Pulp)": {
        "Google News (ANZ Packaging: Paper Bags & Molded Pulp)": "https://news.google.com/rss/search?q=(Australia+OR+%22New+Zealand%22)+(%22paper+bag%22+OR+%22molded+fiber%22+OR+%22moulded+pulp%22+OR+%22paper+packaging%22)+when:14d&hl=en-AU&gl=AU&ceid=AU:en",
        "Google News (ANZ Sustainable Packaging Regulations: APCO)": "https://news.google.com/rss/search?q=(APCO+OR+%22single-use+plastic%22)+(%22paper+packaging%22+OR+packaging+OR+recyclable)+when:14d&hl=en-NZ&gl=NZ&ceid=NZ:en",
    },
    "🇮🇩/🇸🇬/🌏 東南亞主要漿廠與食品容器 (Southeast Asia Pulp & Food Packaging: APP / SCG Packaging)": {
        "Google News (Southeast Asia Pulp: APP / APRIL / Indah Kiat)": "https://news.google.com/rss/search?q=%22Asia+Pulp+Paper%22+OR+%22Indah+Kiat%22+OR+%22Riau+Andalan%22+OR+%22APRIL+Group%22+pulp+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Google News (Southeast Asia Food Packaging & Converting: SCG Packaging / Foopak)": "https://news.google.com/rss/search?q=(%22SCG+Packaging%22+OR+SCGP+OR+Foopak+OR+%22containerboard%22)+(Vietnam+OR+Indonesia+OR+Thailand)+when:14d&hl=en-US&gl=US&ceid=US:en",
        "Yahoo Finance ID (PT Indah Kiat Pulp & Paper - INKP.JK)": "https://finance.yahoo.com/rss/headline?s=INKP.JK",
    },
    "🇹🇼 台灣造紙四大廠 (Taiwan Paper: 正隆 榮成 永豐餘 華紙)": {
        "Google News (台灣紙業: 正隆 榮成 永豐餘 華紙)": "https://news.google.com/rss/search?q=(%E6%AD%A3%E9%9A%86+OR+%E6%A6%AE%E6%88%90+OR+%E6%B0%B8%E8%B1%90%E9%A4%98+OR+%E8%8F%AF%E7%B4%99)+(%E9%80%A0%E7%B4%99+OR+%E5%B7%A5%E7%B4%99+OR+%E7%B4%99%E6%BC%BF+OR+%E7%87%9F%E6%94%B6)+when:14d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
    "🇹🇼 台灣食品包裝與容器 (Taiwan Food Packaging: 紙袋/紙杯/紙模塑/紙盒/非塑容器)": {
        "Google News (台灣紙容器 紙餐盒 紙杯 減塑)": "https://news.google.com/rss/search?q=(%E7%B4%99%E5%AE%B9%E5%99%A8+OR+%E7%B4%99%E9%A4%90%E7%9B%92+OR+%E6%A4%8D%E7%BA%96%E9%A4%90%E7%9B%92+OR+%E9%98%B2%E6%B2%B9%E7%B4%99)+(%E6%B8%9B%E5%A1%91+OR+%E5%8C%85%E8%A3%9D+OR+%E7%84%A1%E6%B0%9F+OR+%E9%A3%9F%E5%AE%89)+when:14d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "Google News (華紙 益利疊 非塑食安 正隆 食品包裝)": "https://news.google.com/rss/search?q=(%E7%9B%8A%E5%88%A9%E7%96%8A+OR+%E9%9D%9E%E5%A1%91%E9%A3%9F%E5%AE%89+OR+%E6%B0%B4%E6%80%A7%E5%A1%97%E5%B1%A4+OR+%E7%B4%99%E5%99%A8%E5%BB%A0+OR+%E7%B4%99%E7%B4%97)+when:14d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    }
}

# ═════════════════════════════════════════════════════════════════════════
# 2. NLP 實體識別、情報源權威分級、反噪音閘門與評分規則
# ═════════════════════════════════════════════════════════════════════════

ENTITY_MAP = {
    "International Paper": "🏢 International Paper",
    "Smurfit Westrock": "🏢 Smurfit Westrock",
    "Smurfit WestRock": "🏢 Smurfit Westrock",
    "Packaging Corp": "🏢 PCA",
    "Packaging Corporation": "🏢 PCA",
    "Graphic Packaging": "🏢 Graphic Packaging",
    "Novolex": "🏢 Novolex (包裝紙袋巨頭)",
    "Pactiv Evergreen": "🏢 Novolex / Pactiv",
    "Huhtamaki": "🏢 Huhtamaki (普樂包裝)",
    "Dart Container": "🏢 Dart Container",
    "Detmold": "🏢 Detmold Group (澳洲包裝)",
    "SCG Packaging": "🏢 SCG Packaging (泰國)",
    "SCGP": "🏢 SCG Packaging (泰國)",
    "UPM": "🏢 UPM-Kymmene",
    "Stora Enso": "🏢 Stora Enso",
    "Mondi": "🏢 Mondi Group",
    "Sappi": "🏢 Sappi",
    "Arauco": "🏢 Arauco Chile",
    "CMPC": "🏢 CMPC",
    "Suzano": "🏢 Suzano",
    "Eldorado": "🏢 Eldorado Brasil",
    "王子": "🏢 王子控股 (Oji)",
    "Oji": "🏢 王子控股 (Oji)",
    "大王": "🏢 大王製紙 (Daio)",
    "Daio": "🏢 大王製紙 (Daio)",
    "日本製紙": "🏢 日本製紙 (NPI)",
    "Nippon Paper": "🏢 日本製紙 (NPI)",
    "北越": "🏢 北越 (Hokuetsu)",
    "ザ・パック": "🏢 The Pack (日本紙袋龍頭)",
    "The Pack": "🏢 The Pack (日本紙袋龍頭)",
    "シモジマ": "🏢 Shimojima (下島包裝)",
    "Shimojima": "🏢 Shimojima (下島包裝)",
    "スーパーバッグ": "🏢 Super Bag (日本包裝袋)",
    "博匯": "🏢 博匯紙業 (APP)",
    "博汇": "🏢 博匯紙業 (APP)",
    "金光": "🏢 金光紙業 (APP)",
    "Asia Pulp": "🏢 APP 金光集團",
    "Foopak": "🏢 APP Foopak (無塑包裝)",
    "Indah Kiat": "🏢 Indah Kiat (APP)",
    "Riau Andalan": "🏢 APRIL / 廖內漿紙",
    "APRIL": "🏢 APRIL / 廖內漿紙",
    "玖龍": "🏢 玖龍紙業 (Nine Dragons)",
    "玖龙": "🏢 玖龍紙業 (Nine Dragons)",
    "Nine Dragons": "🏢 玖龍紙業 (Nine Dragons)",
    "山鷹": "🏢 山鷹國際 (Shanying)",
    "山鹰": "🏢 山鷹國際 (Shanying)",
    "Shanying": "🏢 山鷹國際 (Shanying)",
    "太陽紙業": "🏢 太陽紙業 (Sun Paper)",
    "太阳纸业": "🏢 太陽紙業 (Sun Paper)",
    "Sun Paper": "🏢 太陽紙業 (Sun Paper)",
    "晨鳴": "🏢 晨鳴紙業 (Chenming)",
    "晨鸣": "🏢 晨鳴紙業 (Chenming)",
    "Chenming": "🏢 晨鳴紙業 (Chenming)",
    "眾鑫": "🏢 眾鑫股份 (紙模塑龍頭)",
    "众鑫": "🏢 眾鑫股份 (紙模塑龍頭)",
    "韶能": "🏢 韶能股份 (植纖模塑)",
    "裕同": "🏢 裕同科技",
    "美盈森": "🏢 美盈森",
    "家聯": "🏢 家聯科技",
    "家联": "🏢 家聯科技",
    "Sylvamo": "🏢 Sylvamo",
    "Metsä": "🏢 Metsä Board",
    "Metsa": "🏢 Metsä Board",
    "Billerud": "🏢 Billerud",
    "Pratt": "🏢 Pratt Industries",
    "DS Smith": "🏢 DS Smith (IP)",
    "正隆": "🏢 正隆 (1904)",
    "榮成": "🏢 榮成 (1909)",
    "永豐餘": "🏢 永豐餘 (1907)",
    "華紙": "🏢 華紙 (1905)",
    "中華紙漿": "🏢 華紙 (1905)",
    "益利疊": "🏢 華紙 益利疊 (CircuWell)",
    "CircuWell": "🏢 華紙 益利疊 (CircuWell)",
    "捷比達": "🏢 捷比達 (GPPC)",
    "富利康": "🏢 富利康",
    "永純": "🏢 永純紙業",
    "廣源": "🏢 廣源造紙",
}

TOPIC_KEYWORDS = {
    "價格與調幅": ["price", "pricing", "hike", "漲價", "涨价", "調價", "调价", "提價", "提价", "報價", "报价", "牌價", "per ton", "per tonne", "元/噸", "元/吨", "利差", "spread", "surcharge", "附加費", "凍漲"],
    "產能與營運": ["mill", "capacity", "expansion", "closure", "curtailment", "plant", "產能", "产能", "擴產", "扩产", "停機", "停机", "歲修", "關廠", "投產", "投产", "開工率", "稼動率", "專案", "project"],
    "綠色法規與ESG": ["PPWR", "EUDR", "PFAS", "PFHxA", "GB 4806", "carbon", "decarbonization", "碳費", "環保", "生質能", "無塑", "无塑", "可回收", "永續", "DDS", "禁令", "ban", "lawsuit", "sues"],
    "食品包裝與容器": ["food packaging", "paper packaging", "food container", "tableware", "食品包裝", "食品包装", "食品容器", "餐飲包裝", "外帶包材", "紙容器", "纸容器", "食品級", "食品级"],
    "紙袋與手提包裝": ["paper bag", "kraft bag", "shopping bag", "bakery bag", "SOS bag", "紙袋", "纸袋", "手提袋", "牛皮紙袋", "防油紙袋", "手挽袋"],
    "紙杯與飲品容器": ["paper cup", "hot cup", "cold cup", "beverage cup", "cup sleeve", "aqueous cup", "紙杯", "纸杯", "杯套", "冷熱飲杯", "無塑紙杯", "水性塗層紙杯", "淋膜紙杯"],
    "紙模塑與植纖餐具": ["molded pulp", "molded fiber", "moulded pulp", "bagasse", "plant fiber", "clamshell", "紙模塑", "纸模塑", "植纖", "植纤", "甘蔗渣", "模塑", "漿模", "浆模", "植纖餐盒", "パルプモールド"],
    "食品紙盒與折疊盒": ["folding carton", "food box", "takeaway container", "meal box", "burger box", "pizza box", "紙盒", "纸盒", "餐盒", "折疊盒", "便當盒", "彩盒", "紙パック"],
    "無塑無氟與阻隔塗層": ["PFAS-free", "aqueous barrier", "fluorine-free", "bio-barrier", "greaseproof", "water-based coating", "水性阻隔", "水性塗層", "水性涂层", "無氟", "无氟", "防油紙", "防油纸", "去塑", "脫プラ", "脱プラ", "無塑淋膜", "可堆肥", "可降解", "耐油", "バリア"],
    "包裝禁塑法規與認證": ["single-use plastic", "APCO", "SB 54", "AB 1200", "BPI", "DIN CERTCO", "FSC", "一次性餐具", "禁塑令", "減塑", "减塑", "資源循環", "包裝協議", "食品接觸安全"],
    "能源與海運物流": ["brent", "wti", "crude", "coal", "原油", "煤炭", "scfi", "bdi", "freight", "運費", "航運", "港口", "terminal", "logistics", "深水港", "RNG"],
    "新材料與高階包裝": ["CNF", "nanocellulose", "SHIELDPLUS", "Foopak", "liquid packaging", "液體紙盒", "熱感紙", "阻隔紙", "奈米纖維", "極細木質繊維", "セルロース", "紙紗", "蕉麻"],
    "大宗木片與原料": ["woodchip", "wood chips", "pulpwood", "木片", "原木", "廢紙", "废纸", "OCC", "長纖", "短纖", "闊葉漿", "針葉漿", "NBSK", "BHKP", "pulp"],
    "財報與併購": ["earnings", "revenue", "EBITDA", "quarter", "Q1", "Q2", "Q3", "Q4", "results", "acquisition", "merger", "spin-off", "sale", "營收", "营收", "淨利", "净利", "獲利", "財報", "三季報", "三季报", "併購", "收購", "決算"],
    "貿易救濟與關稅": ["dumping", "countervailing", "tariff", "trade dispute", "關稅", "反傾銷", "反補貼", "雙反", "救濟"]
}

# 負向噪音黑名單 (攔截卡牌遊戲、機器人股評、假市場報告、生活旅遊軟文)
NEGATIVE_PATTERNS = [
    r"マジック：ザ・ギャザリング",
    r"Magic:\s*The\s*Gathering",
    r"スター・トレック",
    r"ブースターパック",
    r"yu-gi-oh",
    r"遊戯王",
    r"Vジャンプ",
    r"シャドバ",
    r"GameWith",
    r"ポケモンカード",
    r"トレカ",
    r"本日の【業種】騰落ランキング",
    r"マーケットカレンダー",
    r"2 surging\s+stocks",
    r"stocks to buy",
    r"stock price, news, quote and history",
    r"Why .* Stock Is Trading (Up|Down) Today",
    r"Why .* Rallied Today",
    r"^Form 4 ",
    r"Dividend Analysis$",
    r"Options Market Predicting a Spike",
    r"Should Value Investors Buy",
    r"机构持仓风向标",
    r"大觉寺",
    r"流水席",
    r"烘焙DIY体验课",
    r"Chiikawa彩绘机",
    r"Market Size, Share, Trends 203\d",
    r"Market in the Middle East: Size, Trends and Forecast",
    r"CAGR Until 203\d - EIN Presswire",
    r"個股概覽\s*\|\s*個股",
    r"Seasonal Returns Chart",
    r"Estimates\s*–\s*IDX:",
    r"trades pre-market at EUR",
    r"Analysts set IDR .* average target",
    r"banana shortage hits",
    r"100元鈔票快變成銅板",
]

# 情報源權威分級 (Tier 1: +1.8, Tier 2: +0.8, Tier 3: -1.2)
TIER1_PUBLISHERS = [
    "packaging dive", "fastmarkets", "risi", "reuters", "bloomberg", "lesprom",
    "fordaq", "wood central", "resource recycling", "recycling today", "pulp & paper",
    "tissue world", "日本経済新聞", "日刊工業新聞", "ニュースイッチ", "時事ドットコム",
    "nhk", "工商時報", "經濟日報", "自由時報", "中央社", "紙業網", "纸业网", "卓創",
    "生意社", "證券時報", "证券时报", "上海證券報", "upm.com", "storaenso.com"
]

TIER2_PUBLISHERS = [
    "packaging gateway", "packaging insights", "food processing", "bnamericas",
    "valor international", "corridor business journal", "central penn business journal",
    "財訊", "鉅亨網", "moneydj", "東方財富", "东方财富", "新浪", "中財網", "中财网",
    "搜狐", "證券之星", "证券之星", "tradingview", "愛媛新聞", "tbs news"
]

TIER3_NOISE_PUBLISHERS = [
    "the motley fool", "barchart", "marketbeat", "simply wall st", "insider monkey",
    "zacks", "investing.com", "ein presswire", "future market insights", "indexbox",
    "株探", "gamewith", "yu-gi-oh.jp"
]


def extract_publisher(clean_title, fallback_source):
    """從 Google News 標題尾端萃取真實發布媒體名稱"""
    if " - " in clean_title:
        parts = clean_title.rsplit(" - ", 1)
        if 1 < len(parts[1]) <= 35:
            return parts[0].strip(), parts[1].strip()
    return clean_title, fallback_source


def evaluate_source_tier(publisher, source_name):
    """判定來源權威等級 (Tier 1 / Tier 2 / Tier 3)"""
    combined = f"{publisher} {source_name}".lower()
    for t3 in TIER3_NOISE_PUBLISHERS:
        if t3 in combined:
            return "Tier 3 (一般聚合)", -1.2
    for t1 in TIER1_PUBLISHERS:
        if t1 in combined:
            return "Tier 1 (權威一手)", 1.8
    for t2 in TIER2_PUBLISHERS:
        if t2 in combined:
            return "Tier 2 (主流專業)", 0.8
    return "Tier 2 (主流專業)", 0.3


def parse_pub_date(pub_date_str):
    """解析 RSS pubDate 並回傳 UTC datetime 與 YYYY-MM-DD 字串"""
    if not pub_date_str:
        return None, ""
    try:
        dt = parsedate_to_datetime(pub_date_str.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt, dt.strftime("%Y-%m-%d")
    except Exception:
        # 嘗試 ISO 格式解析
        m = re.search(r"(\d{4}-\d{2}-\d{2})", pub_date_str)
        if m:
            try:
                dt = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                return dt, m.group(1)
            except Exception:
                pass
    return None, ""


def is_noise_article(title, publisher, entities, topics):
    """多語反噪音與語境消歧閘門"""
    full_text = f"{title} - {publisher}"
    for pat in NEGATIVE_PATTERNS:
        if re.search(pat, full_text, re.IGNORECASE):
            return True, f"Matched negative pattern: {pat}"

    # 消歧規則 1：日本包裝袋檢索避免卡牌「ザ・パック」誤入
    if any(k in full_text for k in ["デッキ", "カード", "コレクション", "ブースター"]):
        if not any(k in full_text for k in ["製紙", "王子", "日本製紙", "段ボール", "紙袋", "パッケージ"]):
            return True, "TCG card pack false positive"

    # 消歧規則 2：若既無造紙實體也無產業主題，檢查是否具備基本造紙/包裝核心詞彙
    if not entities and not topics:
        core_industry_terms = [
            "pulp", "paper", "paperboard", "containerboard", "packaging", "corrugated",
            "fiber", "fibre", "woodchip", "carton", "mill", "tissue",
            "造紙", "造纸", "紙業", "纸业", "紙漿", "纸浆", "木片", "工紙", "工纸",
            "紙箱", "纸箱", "紙器", "纸器", "製紙", "パルプ", "段ボール", "白卡"
        ]
        if not any(term in full_text.lower() for term in core_industry_terms):
            return True, "No industry entity, topic, or core keyword"

    return False, ""


def classify_supply_chain_and_signal(topics, title):
    """自動歸類供應鏈環節與決策信號類別"""
    t_set = set(topics)
    # 供應鏈環節
    if "大宗木片與原料" in t_set:
        stage = "🧪 上中游・木漿/廢紙/木片"
    elif any(k in t_set for k in ["食品包裝與容器", "紙袋與手提包裝", "紙杯與飲品容器", "紙模塑與植纖餐具", "食品紙盒與折疊盒", "無塑無氟與阻隔塗層"]):
        stage = "🍱 下游・食品包裝與替塑容器"
    elif any(k in t_set for k in ["綠色法規與ESG", "包裝禁塑法規與認證", "貿易救濟與關稅"]):
        stage = "⚖️ 政策・全球法規與合規"
    elif "能源與海運物流" in t_set:
        stage = "🚢 總經・能源與海運物流"
    else:
        stage = "🏭 中游・造紙與箱板紙廠"

    # 決策信號類別
    if "價格與調幅" in t_set:
        sig = "🔴 價格與利差信號"
    elif "財報與併購" in t_set:
        sig = "🟢 財報與資本運作"
    elif any(k in t_set for k in ["綠色法規與ESG", "包裝禁塑法規與認證"]):
        sig = "🟠 法規與合規預警"
    elif "產能與營運" in t_set:
        sig = "🟣 產能與工廠動態"
    else:
        sig = "🔵 新材與包裝轉型"

    return stage, sig


def analyze_article(raw_title, source_name):
    headline, publisher = extract_publisher(raw_title, source_name)
    entities = []
    topics = []
    score = 2.5  # 基準分 (調降無實體無主題之基準分，拉開有效信號差距)

    # 1. 實體識別
    for kw, entity_tag in ENTITY_MAP.items():
        if kw.lower() in headline.lower():
            if entity_tag not in entities:
                entities.append(entity_tag)
                score += 1.6

    # 2. 主題識別
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in headline.lower():
                if topic not in topics:
                    topics.append(topic)
                    if topic in ["價格與調幅", "產能與營運", "綠色法規與ESG", "財報與併購"]:
                        score += 1.9
                    elif topic in ["紙袋與手提包裝", "紙模塑與植纖餐具", "紙杯與飲品容器", "無塑無氟與阻隔塗層", "大宗木片與原料"]:
                        score += 1.7
                    else:
                        score += 1.1
                break

    # 3. 抽取關鍵量化數值 (價格、百分比、噸數、金額)
    number_matches = re.findall(
        r'(\+?\$?\d+[\d,\.]*\s*(?:元|萬|億|%|美元|美噸|短噸|萬噸|百萬|十億|億日圓|億元|dollars?|tons?|tonnes?|EUR|RMB|BRL|USD|NT\$|billion|million|/噸|/ton|/MT|/ST))',
        headline,
        re.IGNORECASE,
    )
    if number_matches:
        score += 0.8

    # 4. 情報源權威分級加權
    tier_label, tier_delta = evaluate_source_tier(publisher, source_name)
    score += tier_delta

    score = max(1.0, min(round(score, 1), 10.0))
    stage, signal_type = classify_supply_chain_and_signal(topics, headline)

    return {
        "headline": headline,
        "publisher": publisher,
        "tier": tier_label,
        "entities": entities,
        "topics": topics,
        "numbers": number_matches,
        "score": score,
        "supply_chain_stage": stage,
        "signal_type": signal_type,
    }


def compute_title_tokens(headline):
    """將中英日標題切分為標準化 Token 與雙字元集合，供近重複聚類使用"""
    clean = re.sub(r"[^\w\u4e00-\u9fff\u3040-\u30ff]+", " ", headline.lower()).strip()
    en_tokens = set(w for w in clean.split() if len(w) > 2 and not w.isdigit())
    # 針對中日文萃取連續雙字元 (Bigrams)
    cjk_chars = re.sub(r"[^\u4e00-\u9fff\u3040-\u30ff]", "", headline)
    cjk_bigrams = set(cjk_chars[i:i+2] for i in range(len(cjk_chars) - 1)) if len(cjk_chars) >= 2 else set()
    return en_tokens | cjk_bigrams


def jaccard_similarity(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


# ═════════════════════════════════════════════════════════════════════════
# 3. 高效併發抓取器與四層品質過濾管線 (Concurrent Fetcher & 4-Tier Gate)
# ═════════════════════════════════════════════════════════════════════════

def fetch_single_feed(source_tuple):
    region_name, source_name, url, limit, max_age_days = source_tuple
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    items_data = []
    stats = {"raw_fetched": 0, "expired_dropped": 0, "noise_dropped": 0}
    now_utc = datetime.now(timezone.utc)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
        root = ET.fromstring(content)
        items = root.findall('.//item')[:limit]
        stats["raw_fetched"] = len(items)

        for item in items:
            raw_title = item.find('title').text if item.find('title') is not None else 'No Title'
            clean_title = html.unescape(raw_title.strip())
            pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''

            # [Gate 1] 確定性時效過濾 (剔除超過 max_age_days 的陳舊新聞)
            pub_dt, iso_date = parse_pub_date(pubDate)
            if pub_dt is not None:
                age_days = (now_utc - pub_dt).total_seconds() / 86400.0
                if age_days > max_age_days:
                    stats["expired_dropped"] += 1
                    continue
            else:
                iso_date = now_utc.strftime("%Y-%m-%d")

            analysis = analyze_article(clean_title, source_name)

            # [Gate 2] 反噪音與語境消歧過濾
            is_noise, _ = is_noise_article(
                analysis["headline"],
                analysis["publisher"],
                analysis["entities"],
                analysis["topics"],
            )
            if is_noise:
                stats["noise_dropped"] += 1
                continue

            items_data.append({
                "region": region_name,
                "source": source_name,
                "publisher": analysis["publisher"],
                "tier": analysis["tier"],
                "title": clean_title,
                "headline": analysis["headline"],
                "pub_date": pubDate.strip(),
                "iso_date": iso_date,
                "link": link.strip(),
                "entities": analysis["entities"],
                "topics": analysis["topics"],
                "numbers": analysis["numbers"],
                "supply_chain_stage": analysis["supply_chain_stage"],
                "signal_type": analysis["signal_type"],
                "score": analysis["score"],
                "corroboration_count": 1,
                "_tokens": compute_title_tokens(analysis["headline"]),
            })
    except Exception:
        pass
    return region_name, source_name, items_data, stats


def deduplicate_and_cluster(articles):
    """
    [Gate 3] 語義事件聚類與近重複去重：
    依優先級分數由高至低排序，若後續報導與已入選主報導 Jaccard 相似度 >= 0.45，
    則自動歸併至主報導並累加 corroboration_count (多源交叉印證數)，同時微幅加分。
    """
    sorted_arts = sorted(articles, key=lambda x: (x["score"], x["iso_date"]), reverse=True)
    clusters = []

    for art in sorted_arts:
        norm_hl = re.sub(r"\s+", " ", art["headline"].lower().strip())
        if len(norm_hl) <= 5:
            continue

        merged = False
        for primary in clusters:
            prim_hl = re.sub(r"\s+", " ", primary["headline"].lower().strip())
            if norm_hl == prim_hl:
                primary["corroboration_count"] += 1
                merged = True
                break

            sim = jaccard_similarity(art["_tokens"], primary["_tokens"])
            # 若同一實體且相似度 >= 0.38，或標題直接相似度 >= 0.48，視為同一事件轉載
            same_entity = bool(set(art["entities"]) & set(primary["entities"]))
            if sim >= 0.48 or (same_entity and sim >= 0.36):
                primary["corroboration_count"] += 1
                primary["score"] = min(10.0, round(primary["score"] + 0.3, 1))
                merged = True
                break

        if not merged:
            clusters.append(art)

    # 移除內部計算用 _tokens 欄位並重新按最終分數排序
    for c in clusters:
        c.pop("_tokens", None)
    clusters.sort(key=lambda x: (x["score"], x["corroboration_count"], x["iso_date"]), reverse=True)
    return clusters


def sync_top_signals_to_db(articles, fetch_time_str, stats_summary):
    """將高價值情報自動同步寫入 SQLite `paperluz.db` 的 `industry_news` 與 `pipeline_logs`"""
    if not os.path.exists(DB_PATH):
        return 0
    ingested = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        obs_date = datetime.now().strftime("%Y-%m-%d")

        for art in articles:
            if art["score"] < 6.0:
                continue
            hash_id = hashlib.md5(art["headline"].encode("utf-8")).hexdigest()[:8].upper()
            article_id = f"AUTO_{art['iso_date'].replace('-', '')}_{hash_id}"
            region_code = "GLOBAL"
            if "🇺🇸" in art["region"]:
                region_code = "US"
            elif "🇪🇺" in art["region"]:
                region_code = "EU"
            elif "🇯🇵" in art["region"]:
                region_code = "JP"
            elif "🇨🇳" in art["region"]:
                region_code = "CN"
            elif "🇹🇼" in art["region"]:
                region_code = "TW"
            elif "🇨🇱" in art["region"] or "🇧🇷" in art["region"]:
                region_code = "LATAM"
            elif "🇦🇺" in art["region"] or "🇳🇿" in art["region"]:
                region_code = "ANZ"
            elif "🇮🇩" in art["region"]:
                region_code = "SEA"

            tags_list = art["topics"] + [e.replace("🏢 ", "") for e in art["entities"]]
            tags_json = json.dumps(tags_list, ensure_ascii=False)
            impact = "high" if art["score"] >= 7.5 else "med"
            summary = f"[{art['supply_chain_stage']}｜{art['signal_type']}] 來源: {art['publisher']} ({art['tier']})｜多源印證: {art['corroboration_count']} 篇"

            cur.execute("""
                INSERT INTO industry_news (
                    article_id, title, region, category, tags, publish_date, obs_date,
                    source, source_url, summary, impact_level, selected_for_report, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'candidate')
                ON CONFLICT(article_id) DO UPDATE SET
                    summary=excluded.summary,
                    obs_date=excluded.obs_date,
                    impact_level=excluded.impact_level,
                    updated_at=datetime('now', 'localtime')
            """, (
                article_id, art["headline"], region_code, art["signal_type"],
                tags_json, art["iso_date"], obs_date, art["publisher"],
                art["link"], summary, impact
            ))
            ingested += 1

        run_id = f"NEWS_V6_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cur.execute("""
            INSERT INTO pipeline_logs (run_id, run_date, records_ingested, records_audited, errors_count, status, log_summary)
            VALUES (?, ?, ?, ?, 0, 'SUCCESS', ?)
        """, (run_id, fetch_time_str, ingested, stats_summary["raw_fetched"], json.dumps(stats_summary, ensure_ascii=False)))

        conn.commit()
        conn.close()
    except Exception:
        pass
    return ingested


def run_news_aggregation(save_snapshot=False, quiet=False, top_signals=8, max_age_days=14):
    start_time = datetime.now()
    now_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    date_str = start_time.strftime('%Y-%m-%d')

    if not quiet:
        print(f"[{now_str}] 🚀 啟動 Paperluz 產業情報自動聚合引擎 v6.0 (四層品質閘門＋語義聚類版)...")
        print("=" * 82)

    tasks = []
    for region_name, feeds in REGIONAL_FEEDS.items():
        for source_name, url in feeds.items():
            tasks.append((region_name, source_name, url, 8, max_age_days))

    raw_candidates = []
    gate_stats = {"raw_fetched": 0, "expired_dropped": 0, "noise_dropped": 0}

    # 多線程並行加速
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(fetch_single_feed, task) for task in tasks]
        for future in as_completed(futures):
            region_name, source_name, items, st = future.result()
            gate_stats["raw_fetched"] += st["raw_fetched"]
            gate_stats["expired_dropped"] += st["expired_dropped"]
            gate_stats["noise_dropped"] += st["noise_dropped"]
            raw_candidates.extend(items)

    # 執行全域語義事件聚類與近重複去重
    all_articles = deduplicate_and_cluster(raw_candidates)
    gate_stats["duplicates_merged"] = len(raw_candidates) - len(all_articles)
    gate_stats["clean_signals"] = len(all_articles)

    # 重新組裝分區結構
    categories = {r: [] for r in REGIONAL_FEEDS.keys()}
    by_region_source = {r: {} for r in REGIONAL_FEEDS.keys()}
    for art in all_articles:
        r = art["region"]
        s = art["source"]
        by_region_source[r].setdefault(s, []).append(art)

    for r, src_dict in by_region_source.items():
        for s, arts in src_dict.items():
            categories[r].append({
                "source": s,
                "articles": arts
            })

    # 計算供應鏈環節分布統計
    stage_breakdown = {}
    for art in all_articles:
        st = art["supply_chain_stage"]
        stage_breakdown[st] = stage_breakdown.get(st, 0) + 1

    top_picks = all_articles[:top_signals]

    # 自動同步高分情報至 SQLite 資料庫
    db_synced_count = sync_top_signals_to_db(all_articles, now_str, gate_stats) if save_snapshot else 0

    aggregated_results = {
        "engine_version": "Paperluz Engine v6.0 (Institutional Multi-Tier Gate & Deduplication Edition)",
        "fetch_time": now_str,
        "date": date_str,
        "max_age_days": max_age_days,
        "quality_gate_stats": gate_stats,
        "supply_chain_breakdown": stage_breakdown,
        "total_articles": len(all_articles),
        "top_signals": top_picks,
        "categories": categories
    }

    if not quiet:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"⚡ 抓取與清洗完畢！耗時: {elapsed:.2f}s")
        print(f"🛡️ 【四層品質閘門統計】原始抓取: {gate_stats['raw_fetched']} 則 ➔ 剔除過期(>{max_age_days}天): {gate_stats['expired_dropped']} 則 ｜ 攔截噪音/偽陽性: {gate_stats['noise_dropped']} 則 ｜ 聚類合併重複: {gate_stats['duplicates_merged']} 則 ➔ 淨化高價值情報: {len(all_articles)} 則\n")

        print(f"🔥 【本週 Top {len(top_picks)} 重磅決策信號 (Priority Institutional Signals)】")
        print("-" * 82)
        for idx, item in enumerate(top_picks, 1):
            ent_str = " ".join([f"`{e}`" for e in item["entities"]]) if item["entities"] else ""
            top_str = " ".join([f"[{t}]" for t in item["topics"]]) if item["topics"] else ""
            corr_str = f" 🔥({item['corroboration_count']}源印證)" if item["corroboration_count"] > 1 else ""
            print(f"  {idx}. [{item['score']}★ | {item['signal_type']}] {item['headline']}{corr_str}")
            print(f"     環節: {item['supply_chain_stage']} ｜ 標籤: {ent_str} {top_str}")
            print(f"     日期: {item['iso_date']} ｜ 媒體: {item['publisher']} ({item['tier']})")
        print("=" * 82)

        for region, source_list in categories.items():
            count = sum(len(s["articles"]) for s in source_list)
            print(f"\n📁 【{region}】(共 {count} 則淨化情報)")
            for s in source_list:
                print(f"  ➤ {s['source']} ({len(s['articles'])} 則)")
                for it in s["articles"]:
                    num_tag = f" 📊 {', '.join(it['numbers'])}" if it['numbers'] else ""
                    corr_tag = f" ({it['corroboration_count']}源)" if it['corroboration_count'] > 1 else ""
                    print(f"    • [{it['score']}★] [{it['iso_date']}] {it['headline']} — {it['publisher']}{num_tag}{corr_tag}")

    if save_snapshot:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        json_path = os.path.join(SNAPSHOT_DIR, f"news_snapshot_{date_str}.json")
        md_path = os.path.join(SNAPSHOT_DIR, f"news_snapshot_{date_str}.md")

        # 輸出 JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(aggregated_results, f, ensure_ascii=False, indent=2)

        # 輸出專家級 Markdown 簡報
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Paperluz 全球與亞洲紙業情報週報快照（{date_str}）\n\n")
            f.write(f"> **產出時間**：{now_str} ｜ **系統版本**：Paperluz Engine v6.0 ｜ **淨化有效情報**：{len(all_articles)} 則（原始抓取 {gate_stats['raw_fetched']} 則，剔除過期 {gate_stats['expired_dropped']} 則、攔截噪音 {gate_stats['noise_dropped']} 則、事件聚類合併 {gate_stats['duplicates_merged']} 則）\n\n")

            f.write("## 📊 供應鏈情報環節分布 (Supply Chain Coverage)\n\n")
            f.write("| 供應鏈與決策維度 | 淨化情報數 | 佔比 |\n|:---|:---:|:---:|\n")
            for st_name, st_cnt in sorted(stage_breakdown.items(), key=lambda x: x[1], reverse=True):
                pct = (st_cnt / len(all_articles) * 100) if all_articles else 0
                f.write(f"| {st_name} | **{st_cnt} 則** | {pct:.1f}% |\n")
            f.write("\n---\n\n")

            f.write(f"## 🌟 本週 Top {len(top_picks)} 特急重大決策信號 (Priority Institutional Signals)\n\n")
            for idx, item in enumerate(top_picks, 1):
                ent_str = " ".join([f"`{e}`" for e in item["entities"]])
                top_str = " ".join([f"`#{t}`" for t in item["topics"]])
                corr_badge = f" ｜ **多源印證**：`{item['corroboration_count']} 篇報導`" if item["corroboration_count"] > 1 else ""
                f.write(f"### {idx}. {item['headline']}\n")
                f.write(f"- **重要度評分**：`{item['score']} / 10.0` ｜ **信號屬性**：`{item['signal_type']}` ｜ **供應鏈環節**：`{item['supply_chain_stage']}`{corr_badge}\n")
                if ent_str or top_str:
                    f.write(f"- **實體與主題標籤**：{ent_str} {top_str}\n")
                if item['numbers']:
                    f.write(f"- **關鍵量化數據**：`{', '.join(item['numbers'])}`\n")
                f.write(f"- **發布日期**：`{item['iso_date']}` ｜ **權威來源**：{item['publisher']} (`{item['tier']}`)\n")
                f.write(f"- **原文鏈接**：[閱讀原文]({item['link']})\n\n")

            f.write("---\n\n## 🌐 分區情報彙總 (Regional Intelligence Breakdown)\n\n")
            for region, source_list in categories.items():
                f.write(f"### 📁 {region}\n\n")
                if not source_list:
                    f.write("*本週期無重大異動或待人工補充*\n\n")
                for s in source_list:
                    f.write(f"#### 📌 {s['source']}\n\n")
                    for it in s["articles"]:
                        num_str = f" `(數據: {', '.join(it['numbers'])})`" if it['numbers'] else ""
                        corr_str = f" `[{it['corroboration_count']}源印證]`" if it['corroboration_count'] > 1 else ""
                        f.write(f"- **{it['headline']}** — *{it['publisher']}*{num_str}{corr_str}\n")
                        f.write(f"  - 評分: `{it['score']}` ｜ 環節: `{it['supply_chain_stage']}` ｜ 日期: `{it['iso_date']}` ｜ [連結]({it['link']})\n")
                    f.write("\n")
            f.write("---\n*© 2026 光網資訊 Luznet ∕ Paperluz 產業情報. All rights reserved.*\n")

        if not quiet:
            print(f"\n📄 快照與資料庫落盤完成：\n   - JSON: {json_path}\n   - MD:   {md_path}\n   - DB:   已自動同步 {db_synced_count} 則高分情報至 paperluz.db")

    return aggregated_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paperluz 全球與亞洲紙業情報自動聚合引擎 (v6.0)")
    parser.add_argument("--save", action="store_true", help="自動將抓取結果保存至 Reports/data/news_snapshots/ (JSON + MD) 並同步至 SQLite")
    parser.add_argument("--quiet", action="store_true", help="靜音模式，僅執行與存檔不輸出詳細清單")
    parser.add_argument("--top", type=int, default=8, help="萃取 Top N 條核心信號 (預設 8)")
    parser.add_argument("--days", type=int, default=14, help="時效過濾最大天數 (預設 14 天)")
    args = parser.parse_args()

    run_news_aggregation(save_snapshot=args.save, quiet=args.quiet, top_signals=args.top, max_age_days=args.days)
