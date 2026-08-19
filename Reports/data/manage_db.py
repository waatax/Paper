#!/usr/bin/env python3
"""
Paperluz Enterprise Database & Information Pipeline Manager v12.0
==================================================================

功能說明:
  1. 初始化建置 SQLite 本地資料庫 (paperluz.db) - 包含 9 大關聯表 (新增 price_forecasts 全鏈預測表)
  2. 擴充 CORE 船運費 (SCFI 貨櫃運價、BDI 散裝木片船、近洋線) 與三地能源價格 (原油 Brent/WTI、台灣燃煤/蒸氣成本、中國動力煤/GB能耗、日本進口煤/JEPX)
  3. 導入日本造紙與包裝/印刷/紙袋會社點位 (OJI, DAIO, NPI, Hokuetsu, Shimojima, Super Bag, The Pack, TOPPAN, DNP)
  4. 實現 paperluz.db 與 price_series.csv 雙向無損同步 (Git 版控與 SQL 查詢雙軌)
  5. 儲存與維護每週 50+ 則業界新聞候選庫 (industry_news)，嚴選 12 則高價值區域洞察進入報告
  6. 支援「能源 × 漿價 × 紙價」多維度 1M/3M/6M 預測與敏感度分析模型

版本: v12.0 (2026-08-14 Core Shipping Freight, Tri-Regional Energy & Forecast Matrix Expansion)
"""

import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "paperluz.db")
CSV_FILE = os.path.join(SCRIPT_DIR, "price_series.csv")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_init(args=None):
    """初始化建置 SQLite 表結構與檢視表 (Schema v12.0 Shipping Freight, Energy & Forecast Matrix Expansion)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 大宗價格與庫存表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id TEXT NOT NULL,
        series_name TEXT NOT NULL,
        geo TEXT NOT NULL,
        product TEXT NOT NULL,
        price_type TEXT NOT NULL,
        currency TEXT NOT NULL,
        unit TEXT NOT NULL,
        freq TEXT NOT NULL,
        obs_date TEXT NOT NULL,
        period TEXT NOT NULL,
        value REAL,
        value_low REAL,
        value_high REAL,
        delta REAL,
        delta_unit TEXT,
        source TEXT NOT NULL,
        source_url TEXT,
        confidence TEXT CHECK(confidence IN ('high', 'med', 'low', 'none')),
        note TEXT,
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(series_id, obs_date, price_type)
    );
    """)

    # 2. 每日匯率表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fx_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair TEXT NOT NULL,          -- USDTWD, USDBRL, USDCNY, EURUSD
        base_ccy TEXT NOT NULL,
        quote_ccy TEXT NOT NULL,
        rate REAL NOT NULL,
        obs_date TEXT NOT NULL,
        change_amount REAL,
        change_pct REAL,
        source TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(pair, obs_date)
    );
    """)

    # 3. 台灣上市紙廠營收與自結獲利表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_revenues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,    -- 1904, 1905, 1907, 1909
        company_name TEXT NOT NULL,
        year_month TEXT NOT NULL,    -- YYYY-MM
        revenue_ntd_hundred_m REAL,  -- 億元
        mom_pct REAL,
        yoy_pct REAL,
        cum_revenue_hundred_m REAL,
        pretax_profit_hundred_m REAL,
        note TEXT,
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(stock_code, year_month)
    );
    """)

    # 4. 產業事件與法規倒數表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS industry_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_code TEXT NOT NULL,
        event_name TEXT NOT NULL,
        category TEXT NOT NULL,      -- REGULATION, DOWNTIME, CAPACITY
        geo TEXT NOT NULL,
        target_date TEXT NOT NULL,
        days_remaining INTEGER,
        status TEXT NOT NULL,
        summary TEXT,
        source TEXT,
        source_url TEXT,
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(event_code, target_date)
    );
    """)

    # 5. 全球情報資訊源註冊表 (Source Registry v12.0 - 含能源、海運、日本紙廠與北美紙袋)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_registry (
        source_id TEXT PRIMARY KEY,
        source_name TEXT NOT NULL,
        geo TEXT NOT NULL,           -- TW, CN, JP, US, EU, GLOBAL
        category TEXT NOT NULL,      -- RAW_MATERIAL, PAPER_MILL, PACKAGING, PRINTING, REGULATION, MACRO_FX_LOGISTICS, CORPORATE, PAPER_BAG, ENERGY, FREIGHT
        tier TEXT NOT NULL CHECK(tier IN ('Level_1', 'Level_2', 'Level_3')), -- 甲級, 乙級, 丙級
        access_type TEXT NOT NULL,   -- API, RSS, SEC_EDGAR, MOPS, HTML_SCRAPE, SEARCH_TEMPLATE
        url_pattern TEXT NOT NULL,
        update_freq TEXT NOT NULL,   -- DAILY, WEEKLY, MONTHLY, EVENT_DRIVEN
        data_provided TEXT,
        reliability_rating TEXT CHECK(reliability_rating IN ('high', 'med', 'low')),
        status TEXT DEFAULT 'active',
        last_verified_at TEXT,
        notes TEXT,
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # 6. Pipeline 執行日誌表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pipeline_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        run_date TEXT NOT NULL,
        records_ingested INTEGER DEFAULT 0,
        records_audited INTEGER DEFAULT 0,
        errors_count INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        log_summary TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # 7. 每週產業新聞與情報候選庫
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS industry_news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id TEXT NOT NULL,
        title TEXT NOT NULL,
        region TEXT NOT NULL,         -- TW, CN, JP, US, EU, GLOBAL, APAC
        category TEXT NOT NULL,       -- RAW_MATERIAL, PAPER_MILL, PACKAGING, REGULATION, LOGISTICS, CORPORATE, PRINTING, DOWNTIME, INDUSTRY_TREND, PAPER_BAG, ENERGY
        tags TEXT NOT NULL,           -- JSON array string
        publish_date TEXT NOT NULL,   -- YYYY-MM-DD
        obs_date TEXT NOT NULL,       -- Date recorded in pipeline YYYY-MM-DD
        source TEXT NOT NULL,
        source_url TEXT,
        summary TEXT NOT NULL,
        impact_level TEXT CHECK(impact_level IN ('high', 'med', 'low')),
        selected_for_report INTEGER DEFAULT 0,
        status TEXT DEFAULT 'candidate' CHECK(status IN ('candidate', 'approved', 'archived')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(article_id)
    );
    """)

    # 8. 全鏈預測矩陣表 (Price Forecasts v12.0)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_item TEXT NOT NULL,    -- CRUDE_OIL, COAL_TW, COAL_CN, COAL_JP, FREIGHT_SCFI, NBSK, BHKP, CONTAINERBOARD, WHITECARD, CULTURAL, TISSUE
        category TEXT NOT NULL,       -- ENERGY, FREIGHT, PULP, PAPER
        horizon TEXT NOT NULL,        -- 1M, 3M, 6M
        target_price_range TEXT NOT NULL,
        trend_direction TEXT NOT NULL, -- Bullish, Neutral, Bearish
        probability_pct INTEGER NOT NULL,
        catalysts TEXT NOT NULL,
        scenario_base TEXT,
        scenario_bull TEXT,
        scenario_bear TEXT,
        margin_impact_bps INTEGER,
        obs_date TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(target_item, horizon, obs_date)
    );
    """)

    # Seed 60 Multi-Region Disclosure Sources into source_registry
    sources_seed = [
        # --- 船運費與海運物流 (FREIGHT & LOGISTICS) ---
        ("SRC_CN_SSE_SCFI", "上海航運交易所 (SSE SCFI)", "CN", "MACRO_FX_LOGISTICS", "Level_1", "API", "https://www.sse.net.cn/", "WEEKLY", "上海出口集裝箱運價指數 (SCFI, 美西/美東/歐線)", "high", "active", "2026-08-14", "全球貨櫃航運價格權威"),
        ("SRC_GLOBAL_BALTIC_BDI", "波羅的海交易所 (Baltic Exchange BDI)", "GLOBAL", "MACRO_FX_LOGISTICS", "Level_1", "API", "https://www.balticexchange.com/", "DAILY", "波羅的海乾散貨指數 (BDI) 與散裝木片船租金", "high", "active", "2026-08-14", "散裝船運價權威"),
        ("SRC_TW_SHIPPING_INTRA", "台灣港務公司/近洋航運統計", "TW", "MACRO_FX_LOGISTICS", "Level_2", "HTML_SCRAPE", "https://www.twport.com.tw/", "WEEKLY", "台灣-東南亞/華東/日本近洋貨櫃運價", "high", "active", "2026-08-14", "近洋短程航線運價"),

        # --- 能源：原油與三地動力煤 (ENERGY: Crude Oil & Coal in TW/CN/JP) ---
        ("SRC_GLOBAL_ICE_BRENT", "倫敦洲際交易所 (ICE Brent Crude)", "GLOBAL", "MACRO_FX_LOGISTICS", "Level_1", "DAILY", "https://www.theice.com/products/219/Brent-Crude-Futures", "DAILY", "布蘭特原油期貨 ($/桶) 與船用燃油基準", "high", "active", "2026-08-14", "全球原油定價錨"),
        ("SRC_GLOBAL_NYMEX_WTI", "紐約商業交易所 (NYMEX WTI)", "GLOBAL", "MACRO_FX_LOGISTICS", "Level_1", "DAILY", "https://www.cmegroup.com/", "DAILY", "西德州輕原油期貨結算價 ($/桶)", "high", "active", "2026-08-14", "北美原油基準"),
        ("SRC_GLOBAL_NEWCASTLE_COAL", "澳洲 Newcastle 動力煤 (globalCOAL)", "GLOBAL", "MACRO_FX_LOGISTICS", "Level_1", "DAILY", "https://www.globalcoal.com/", "DAILY", "亞太動力煤定價錨 FOB Newcastle ($/噸)", "high", "active", "2026-08-14", "亞太動力煤定價權威"),
        ("SRC_TW_TPC_COAL", "台灣電力公司/經濟部能源署 (Taipower Coal)", "TW", "MACRO_FX_LOGISTICS", "Level_1", "HTML_SCRAPE", "https://www.taipower.com.tw/", "MONTHLY", "台灣進口燃煤到港價、汽電共生蒸氣成本指標", "high", "active", "2026-08-14", "台灣造紙熱電成本基準"),
        ("SRC_CN_ZCE_COAL", "鄭州商品交易所 (ZCE 動力煤期貨 ZC)", "CN", "MACRO_FX_LOGISTICS", "Level_1", "API", "http://www.czce.com.cn/", "DAILY", "中國動力煤期貨主力結算價、秦皇島5500大卡平倉價", "high", "active", "2026-08-14", "中國自備電廠熱電成本基準"),
        ("SRC_JP_COAL_CIF", "日本財務省貿易統計 / 資源能源廳", "JP", "MACRO_FX_LOGISTICS", "Level_1", "HTML_SCRAPE", "https://www.customs.go.jp/toukei/info/", "MONTHLY", "日本進口動力煤 CIF 均價 ($/噸) 與 JEPX 電力基準", "high", "active", "2026-08-14", "日本造紙能源成本基準"),

        # --- 日本三大造紙與特種紙巨頭 (JP Paper Mills) ---
        ("SRC_JP_JPA", "日本製紙連合會 (Japan Paper Association)", "JP", "INDUSTRY_TREND", "Level_1", "HTML_SCRAPE", "https://www.jpa.gr.jp/stats/", "MONTHLY", "紙與紙板產銷統計、進出口速報、CO2減排", "high", "active", "2026-08-12", "官方造紙協會權威數據"),
        ("SRC_JP_OJI", "王子控股 / 王子製紙 (Oji Holdings IR 3861.T)", "JP", "CORPORATE", "Level_1", "HTML_SCRAPE", "https://www.ojiholdings.co.jp/en/ir/", "EVENT_DRIVEN", "財報、價格修訂公告、海外紙漿擴產", "high", "active", "2026-08-12", "日本第一大造紙集團"),
        ("SRC_JP_NIPPON", "日本製紙 (Nippon Paper NPI IR 3863.T)", "JP", "CORPORATE", "Level_1", "HTML_SCRAPE", "https://www.nipponpapergroup.com/english/ir/", "EVENT_DRIVEN", "特種紙、包裝紙停機維修、紙容器回收", "high", "active", "2026-08-12", "日本第二大造紙集團"),
        ("SRC_JP_DAIO", "大王製紙 (Daio Paper IR 3880.T)", "JP", "CORPORATE", "Level_1", "HTML_SCRAPE", "https://www.daio-paper.co.jp/en/ir/", "EVENT_DRIVEN", "家庭用紙、工紙牌價調整、衛生紙進口動態", "high", "active", "2026-08-12", "家紙與紙板龍頭"),
        ("SRC_JP_HOKUETSU", "北越 Corporation (Hokuetsu IR 3865.T)", "JP", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.hokuetsucorp.com/en/ir/", "EVENT_DRIVEN", "高階白紙板、印刷用紙、新潟紙漿廠稼動率", "high", "active", "2026-08-12", "日本三大高級紙板廠之一"),
        ("SRC_JP_MITSUBISHI", "三菱製紙 (Mitsubishi Paper Mills 3864.T)", "JP", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.mpm.co.jp/company/ir/", "EVENT_DRIVEN", "特種印刷紙、熱敏紙、感光紙板價格與財報", "high", "active", "2026-08-12", "特種紙會社"),

        # --- 日本包裝、印刷與紙袋加工會社 (JP Packaging, Printing & Paper Bags) ---
        ("SRC_JP_THEPACK", "ザ・パック (The Pack Corp IR 3950.T)", "JP", "PAPER_BAG", "Level_1", "HTML_SCRAPE", "https://www.thepack.co.jp/ir/", "MONTHLY", "日本第一大紙袋市佔廠、手提紙袋、購物袋、牛皮紙袋", "high", "active", "2026-08-12", "日本紙袋龍頭會社"),
        ("SRC_JP_SUPERBAG", "スーパーバッグ (Super Bag IR 3945.T)", "JP", "PAPER_BAG", "Level_1", "HTML_SCRAPE", "https://www.superbag.co.jp/ir/", "EVENT_DRIVEN", "零售紙袋、外帶紙袋、牛皮紙袋與環保包材", "high", "active", "2026-08-12", "紙袋與包裝專業製造會社"),
        ("SRC_JP_SHIMOJIMA", "シモジマ (Shimojima IR 7482.T)", "JP", "PACKAGING", "Level_1", "HTML_SCRAPE", "https://www.shimojima.co.jp/ir/", "MONTHLY", "包裝資材專門商社、店舖紙袋、包裝紙、牛皮紙箱", "high", "active", "2026-08-12", "日本包裝資材與紙袋流通龍頭"),
        ("SRC_JP_RENGO", "連合製紙 / Tri-Wall (Rengo IR 3941.T)", "JP", "PACKAGING", "Level_1", "HTML_SCRAPE", "https://www.rengo.co.jp/english/ir/", "EVENT_DRIVEN", "瓦楞紙箱、包裝自動化設備、重包裝紙箱", "high", "active", "2026-08-12", "日本瓦楞包裝龍頭"),
        ("SRC_JP_TOPPAN", "TOPPAN Holdings (凸版印刷 7911.T)", "JP", "PRINTING", "Level_1", "HTML_SCRAPE", "https://www.holdings.toppan.com/ja/ir/", "EVENT_DRIVEN", "高階包裝印刷、軟包裝、無塑淋膜、數位印刷", "high", "active", "2026-08-12", "日本印刷與高階包裝龍頭"),
        ("SRC_JP_DNP", "大日本印刷 (DNP 7912.T)", "JP", "PRINTING", "Level_1", "HTML_SCRAPE", "https://www.dnp.co.jp/ir/", "EVENT_DRIVEN", "包裝材料、環境對應型紙容器、商業印刷", "high", "active", "2026-08-12", "日本綜合印刷與包裝巨頭"),
        ("SRC_JP_CAA", "日本消費者廳 (CAA Positive List)", "JP", "REGULATION", "Level_1", "HTML_SCRAPE", "https://www.caa.go.jp/policies/policy/standards_evaluation/appliance/positive_list_new", "EVENT_DRIVEN", "食品接觸材質正面表列與紙類界線法規", "high", "active", "2026-08-12", "食品包裝合規關鍵"),

        # --- 北美牛皮紙袋與紙袋專用點位 (US Paper Bag & Kraft Paper) ---
        ("SRC_US_NOVOLEX", "Novolex / Duro Bag (North America)", "US", "PAPER_BAG", "Level_1", "HTML_SCRAPE", "https://novolex.com/newsroom/", "EVENT_DRIVEN", "北美牛皮紙袋(Kraft Paper Bag)、快餐紙袋、禁塑替代", "high", "active", "2026-08-12", "北美第一大紙袋與包裝製造商"),
        ("SRC_US_FASTMARKETS_BAG", "Fastmarkets Kraft Paper & Bag Index", "US", "PAPER_BAG", "Level_2", "HTML_SCRAPE", "https://www.fastmarkets.com/insights/kraft-paper/", "MONTHLY", "北美未漂白牛皮紙 (Unbleached Kraft Paper) 與紙袋價", "high", "active", "2026-08-12", "牛皮紙與紙袋價格指數"),

        # --- 中國 (CN) ---
        ("SRC_CN_SHFE_SP", "上海期貨交易所 (SHFE 紙漿期貨 SP)", "CN", "RAW_MATERIAL", "Level_1", "API", "https://www.shfe.com.cn/statements/dataview/tradeconf/", "DAILY", "漂針漿期貨日結算價、收盤價、持倉量、倉單", "high", "active", "2026-08-12", "亞洲針葉漿期貨價格風向標"),
        ("SRC_CN_SCI99", "卓創資訊 (Sci99)", "CN", "RAW_MATERIAL", "Level_2", "HTML_SCRAPE", "https://www.sci99.com/pulp/", "DAILY", "國產廢紙、進口木漿現貨價、港口庫存、提價函", "high", "active", "2026-08-12", "中國大宗紙業商情權威"),
        ("SRC_CN_100PPI", "生意社 (100ppi)", "CN", "RAW_MATERIAL", "Level_2", "HTML_SCRAPE", "https://www.100ppi.com/vane/detail-1053.html", "DAILY", "針葉漿/闊葉漿基準價、廢紙收購價、基差", "high", "active", "2026-08-12", "現貨與期貨對比資料"),
        ("SRC_CN_CPA", "中國造紙協會 (China Paper Association)", "CN", "INDUSTRY_TREND", "Level_1", "HTML_SCRAPE", "http://www.chinappi.org/", "MONTHLY", "全國紙及紙板產量、進出口統計、產業政策", "high", "active", "2026-08-12", "官方行業協會"),
        ("SRC_CN_NDPAPER", "玖龍紙業 IR (2689.HK)", "CN", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.ndpaper.com/tc/investor/announcements.php", "EVENT_DRIVEN", "中期/年度業績、白卡紙/箱板紙漲價函", "high", "active", "2026-08-12", "亞洲最大工紙造紙集團"),
        ("SRC_CN_LEEMAN", "理文造紙 IR (2314.HK)", "CN", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "http://www.leemanpaper.com/investor.html", "EVENT_DRIVEN", "包裝紙、衛生紙產能、海外造紙基地", "high", "active", "2026-08-12", "工紙龍頭"),
        ("SRC_CN_SUNPAPER", "太陽紙業 IR (002078.SZ)", "CN", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "http://www.sunpapergroup.com/investor.html", "EVENT_DRIVEN", "文化紙、老撾林漿紙一體化產能、月度經營", "high", "active", "2026-08-12", "文化紙與漿紙一體化龍頭"),
        ("SRC_CN_SHANYING", "山鷹國際 IR (600567.SH)", "CN", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "http://www.shanyingintl.com/investor.html", "EVENT_DRIVEN", "再生廢紙回收、北置產能、瓦楞紙箱報價", "high", "active", "2026-08-12", "A股工紙龍頭"),
        ("SRC_CN_BOHUI", "博匯紙業 IR (600966.SH)", "CN", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "http://www.bohui-paper.com/", "EVENT_DRIVEN", "APP旗下白卡紙、食品卡紙調價公告", "high", "active", "2026-08-12", "白卡紙巨頭"),
        ("SRC_CN_CHENMING", "晨鳴紙業 IR (000488.SZ)", "CN", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "http://www.chenmingpaper.com/", "EVENT_DRIVEN", "銅版紙、白卡紙、自製木漿產量與財報", "high", "active", "2026-08-12", "銅版紙龍頭"),
        ("SRC_CN_SAMR_GB", "國家市場監督管理總局 (SAMR/GB標準)", "CN", "REGULATION", "Level_1", "HTML_SCRAPE", "https://openstd.samr.gov.cn/", "EVENT_DRIVEN", "GB 4806.10-2025食品接觸塗料、GB 31825能耗限額", "high", "active", "2026-08-12", "中國國家標準強制執行節點"),

        # --- 台灣 (TW) ---
        ("SRC_TW_MOPS", "公開資訊觀測站 (MOPS)", "TW", "CORPORATE", "Level_1", "MOPS_API", "https://mops.twse.com.tw/", "MONTHLY", "台灣四大紙廠(1904,1905,1907,1909)月營收、重訊、財報", "high", "active", "2026-08-12", "台灣法定資訊揭露節點"),
        ("SRC_TW_1904", "正隆股份有限公司 (Cheng Loong IR)", "TW", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.clc.com.tw/investor/", "EVENT_DRIVEN", "平陽三期投產、紙箱報價、永續報告", "high", "active", "2026-08-12", "台灣第一大工紙廠 1904.TW"),
        ("SRC_TW_1905", "中華紙漿 (Chung Hwa Pulp IR)", "TW", "RAW_MATERIAL", "Level_1", "HTML_SCRAPE", "https://www.chp.com.tw/news/detail/402", "EVENT_DRIVEN", "漿價傳導、益思無塑防油卡紙、綠能汽電共生", "high", "active", "2026-08-12", "台灣唯一文化紙與木漿廠 1905.TW"),
        ("SRC_TW_1907", "永豐餘消費品/投控 (YFY IR)", "TW", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.yfy.com/zh-hant/investors/", "EVENT_DRIVEN", "家紙五月花、碳管理佈局、越南包裝廠", "high", "active", "2026-08-12", "造紙投控龍頭 1907.TW"),
        ("SRC_TW_1909", "榮成紙業 (Long Chen Paper IR)", "TW", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.longchenpaper.com/investor/", "EVENT_DRIVEN", "自結稅前盈餘、中國廠區產能稼動率", "high", "active", "2026-08-12", "工紙大廠 1909.TW"),
        ("SRC_TW_CBC", "中央銀行外匯統計 (CBC)", "TW", "MACRO_FX_LOGISTICS", "Level_1", "HTML_SCRAPE", "https://www.cbc.gov.tw/tw/lp-645-1.html", "DAILY", "USD/TWD 新台幣銀行間收盤匯率", "high", "active", "2026-08-12", "進口原料成本計算基準"),
        ("SRC_TW_MOENV", "環境部氣候變遷署/資源循環署", "TW", "REGULATION", "Level_1", "HTML_SCRAPE", "https://www.moenv.gov.tw/", "EVENT_DRIVEN", "《資源循環推動法》、碳費自主減量費率與開徵", "high", "active", "2026-08-12", "台灣減塑與碳費主管機關"),

        # --- 美國 / 北美 (US) ---
        ("SRC_US_SEC_EDGAR", "美國 SEC EDGAR 申報系統", "US", "CORPORATE", "Level_1", "SEC_EDGAR", "https://www.sec.gov/edgar/searchedgar/companysearch", "EVENT_DRIVEN", "IP, SW, PCA, Suzano 8-K / 10-Q 季報與調價申報", "high", "active", "2026-08-12", "美股法務與財報金標準"),
        ("SRC_US_FASTMARKETS", "Fastmarkets RISI", "US", "RAW_MATERIAL", "Level_2", "HTML_SCRAPE", "https://www.fastmarkets.com/insights/", "WEEKLY", "US OCC美廢出口FAS價、NBSK/BHK牌價、紙板調價監控", "high", "active", "2026-08-12", "全球漿紙定價權威指標"),
        ("SRC_US_PACKAGINGDIVE", "Packaging Dive", "US", "PACKAGING", "Level_2", "HTML_SCRAPE", "https://www.packagingdive.com/", "DAILY", "北美箱板紙漲價(PCA/IP/SW)、紙廠永久關廠、PFAS州法", "high", "active", "2026-08-12", "北美包裝產業即時新聞首選"),
        ("SRC_US_IP", "International Paper IR", "US", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.internationalpaper.com/investors", "EVENT_DRIVEN", "Pine Hill廠關閉、9/1 +$80/噸箱板紙調價", "high", "active", "2026-08-12", "全球包裝巨頭 NYSE:IP"),
        ("SRC_US_SW", "Smurfit WestRock IR", "US", "PACKAGING", "Level_1", "HTML_SCRAPE", "https://www.smurfitwestrock.com/investors", "EVENT_DRIVEN", "合併後財報、歐洲+€120調價、折疊彩盒廠整合", "high", "active", "2026-08-12", "全球最大紙箱與包裝集團 NYSE:SW"),
        ("SRC_US_PCA", "Packaging Corp of America IR", "US", "PACKAGING", "Level_1", "HTML_SCRAPE", "https://ir.packagingcorp.com/", "EVENT_DRIVEN", "+$140/噸歷史級箱板紙漲價、強勁出貨率", "high", "active", "2026-08-12", "北美工紙三雄之一 NYSE:PKG"),
        ("SRC_US_GPI", "Graphic Packaging Intl IR", "US", "PACKAGING", "Level_1", "HTML_SCRAPE", "https://investors.graphicpkg.com/", "EVENT_DRIVEN", "食品塗佈紙板、CRB/SBS廢紙基彩盒產能", "high", "active", "2026-08-12", "食品包裝與彩盒龍頭 NYSE:GPK"),

        # --- 歐洲 (EU) ---
        ("SRC_EU_EURLEX", "歐盟 EUR-Lex 法規公報", "EU", "REGULATION", "Level_1", "HTML_SCRAPE", "https://eur-lex.europa.eu/", "EVENT_DRIVEN", "PPWR Regulation (EU) 2025/40, PFAS 25ppb限制, BPA 2024/3190", "high", "active", "2026-08-12", "歐盟法律生效官方來源"),
        ("SRC_EU_ECHA", "歐洲化學品管理局 (ECHA REACH)", "EU", "REGULATION", "Level_1", "HTML_SCRAPE", "https://echa.europa.eu/", "EVENT_DRIVEN", "PFHxA 條款、食品包裝化學物質限制清單", "high", "active", "2026-08-12", "化學品監管權威"),
        ("SRC_EU_STORAENSO", "Stora Enso IR", "EU", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.storaenso.com/en/investors", "EVENT_DRIVEN", "Oulu 55萬噸消費紙板投產、Skutskär絨毛漿轉型", "high", "active", "2026-08-12", "北歐林漿紙巨頭 OMX:STERV"),
        ("SRC_EU_UPM", "UPM-Kymmene IR", "EU", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://www.upm.com/investors/", "EVENT_DRIVEN", "烏拉圭Paso de los Toros漿廠放量、WISA掛牌", "high", "active", "2026-08-12", "北歐紙漿與生質材料巨頭 OMX:UPM1V"),
        ("SRC_EU_MONDI", "Mondi Group IR", "EU", "PACKAGING", "Level_1", "HTML_SCRAPE", "https://www.mondigroup.com/investors/", "EVENT_DRIVEN", "Schumacher Packaging收購案、瓦楞紙與食品紙袋", "high", "active", "2026-08-12", "歐洲包裝與袋用牛皮紙巨頭 LSE:MNDI"),

        # --- 全球漿廠 (GLOBAL / Latin America) ---
        ("SRC_GLOBAL_SUZANO", "Suzano S.A. IR (Brazil)", "GLOBAL", "RAW_MATERIAL", "Level_1", "SEC_EDGAR", "https://ir.suzano.com.br/", "EVENT_DRIVEN", "Cerrado 255萬噸短纖漿產線淨價($562/噸)、出口月報", "high", "active", "2026-08-12", "全球最大桉木短纖漿生產商 NYSE:SUZ"),
        ("SRC_GLOBAL_ARAUCO", "Arauco (Chile)", "GLOBAL", "RAW_MATERIAL", "Level_1", "HTML_SCRAPE", "https://www.arauco.com/en/investors/", "MONTHLY", "MAPA 專案產能、亞洲漂針漿/漂闊漿外盤牌價公告", "high", "active", "2026-08-12", "智利木漿巨頭"),
        ("SRC_GLOBAL_KLABIN", "Klabin S.A. (Brazil)", "GLOBAL", "PAPER_MILL", "Level_1", "HTML_SCRAPE", "https://ri.klabin.com.br/en/", "EVENT_DRIVEN", "Puma II 塗佈白卡與Klabin紙漿產能", "high", "active", "2026-08-12", "巴西最大綜合造紙廠 B3:KLBN11"),
        ("SRC_GLOBAL_CMPC", "CMPC (Chile)", "GLOBAL", "RAW_MATERIAL", "Level_1", "HTML_SCRAPE", "https://ir.cmpc.com/", "EVENT_DRIVEN", "智利與巴西木漿產量、亞洲牌價", "high", "active", "2026-08-12", "智利紙業雙雄之一"),
        ("SRC_GLOBAL_MERCER", "Mercer International IR", "GLOBAL", "RAW_MATERIAL", "Level_1", "SEC_EDGAR", "https://www.mercerint.com/investors/", "EVENT_DRIVEN", "德國與北美 NBSK 長纖漿產能與現金成本", "high", "active", "2026-08-12", "全球主要長纖漿商品廠 NASDAQ:MERC")
    ]

    for s in sources_seed:
        cursor.execute("""
        INSERT INTO source_registry (
            source_id, source_name, geo, category, tier, access_type, url_pattern,
            update_freq, data_provided, reliability_rating, status, last_verified_at, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            source_name=excluded.source_name,
            geo=excluded.geo,
            category=excluded.category,
            tier=excluded.tier,
            access_type=excluded.access_type,
            url_pattern=excluded.url_pattern,
            update_freq=excluded.update_freq,
            data_provided=excluded.data_provided,
            reliability_rating=excluded.reliability_rating,
            status=excluded.status,
            last_verified_at=excluded.last_verified_at,
            notes=excluded.notes,
            updated_at=datetime('now', 'localtime')
        """, s)

    # 寫入台灣四大紙廠 2026-07 營收預設 seed
    companies = [
        ("1904", "正隆", "2026-07", 42.56, 9.75, 22.82, 263.63, 16.08, "創近19個月新高，平陽三期40萬噸投產放量，上半年稅後淨利16.08億"),
        ("1909", "榮成", "2026-07", 43.24, -8.18, 20.32, 285.35, 4.29, "前7月自結稅前轉盈達4.29億元，8/12宣布分割轉型控股公司"),
        ("1907", "永豐餘", "2026-07", 65.50, -0.79, 6.30, 444.09, 7.79, "上半年稅後淨利7.79億由虧轉盈創5年同期新高，元太貢獻10.91億"),
        ("1905", "華紙", "2026-07", 14.98, -1.28, -10.90, 105.78, -5.79, "第三季啟動減產保價回收現金，加速無塑防油卡紙與生質綠電")
    ]
    for c in companies:
        cursor.execute("""
        INSERT INTO company_revenues (stock_code, company_name, year_month, revenue_ntd_hundred_m, mom_pct, yoy_pct, cum_revenue_hundred_m, pretax_profit_hundred_m, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stock_code, year_month) DO UPDATE SET
            revenue_ntd_hundred_m=excluded.revenue_ntd_hundred_m,
            mom_pct=excluded.mom_pct,
            yoy_pct=excluded.yoy_pct,
            cum_revenue_hundred_m=excluded.cum_revenue_hundred_m,
            pretax_profit_hundred_m=excluded.pretax_profit_hundred_m,
            note=excluded.note,
            updated_at=datetime('now', 'localtime')
        """, c)

    # 寫入產業事件與法規倒數 seeds
    events_seed = [
        ("REG_EU_PPWR", "歐盟包裝與包裝廢棄物法規 (PPWR, (EU) 2025/40) 正式強制生效", "REGULATION", "EU", "2026-08-12", 0, "ACTIVE", "歐盟PPWR法規2026-08-12正式生效，食品接觸紙包裝強制稽核PFAS限額（單一25ppb/總量50ppm）與DPP數位產品護照", "EUR-Lex", "https://eur-lex.europa.eu/"),
        ("CORP_LONGCHEN_SPLIT", "榮成紙業（1909）分割轉型投資控股公司與子公司「榮成低碳紙箱」", "CAPACITY", "TW", "2027-01-04", 139, "ACTIVE", "榮成董事會決議分割台灣工紙與紙箱事業讓與100%子公司榮成低碳紙箱，母公司更名為榮成投資控股，分割基準日訂為2027-01-04", "公開資訊觀測站", "https://mops.twse.com.tw/"),
        ("REG_CN_GB4806_10", "中國 GB 4806.10-2025 食品接觸用塗料及塗層新規強制生效", "REGULATION", "CN", "2026-09-02", 15, "UPCOMING", "中國食品接觸用塗料及塗層新規正式適用，紙杯、紙盒及食品包裝淋膜與印刷塗層納入強制標準管理", "國家標準委", "https://openstd.samr.gov.cn/"),
        ("PRICE_US_CTNBD_0901", "北美三大工紙巨頭 (PCA/Smurfit/IP) 第三輪箱板紙漲價生效", "CAPACITY", "US", "2026-09-01", 14, "UPCOMING", "PCA (+140美元)、Smurfit Westrock (+100美元)、IP (+80美元) 箱板紙漲價9/1正式生效，Raw Material Spread突破$720歷史高點", "Packaging Dive", "https://www.packagingdive.com/"),
        ("REG_EU_PFHXA_BAN", "歐盟 REACH PFHxA 全氟己酸限制條款適用倒數", "REGULATION", "EU", "2026-10-11", 54, "UPCOMING", "歐盟REACH框架下PFHxA及其相關物質在食品包裝紙與紡織塗層之限制全面生效，過渡期僅剩54天", "ECHA", "https://echa.europa.eu/")
    ]
    for e in events_seed:
        cursor.execute("""
        INSERT INTO industry_events (event_code, event_name, category, geo, target_date, days_remaining, status, summary, source, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_code, target_date) DO UPDATE SET
            days_remaining=excluded.days_remaining,
            status=excluded.status,
            summary=excluded.summary,
            updated_at=datetime('now', 'localtime')
        """, e)

    # 寫入全鏈預測矩陣種子資料 (price_forecasts v12.0)
    forecasts_seed = [
        ("CRUDE_OIL", "ENERGY", "1M", "$78–83 / 桶", "Neutral", 65, "OPEC+ 減產維持但歐美煉油旺季進入尾聲", "油價區間盤整，紙廠燃油附加費與化工膠乳成本可控", "中東地緣升級推升油價至 $88 以上", "全球需求疲軟油價回落至 $72", 20, "2026-08-14"),
        ("CRUDE_OIL", "ENERGY", "3M", "$75–80 / 桶", "Bearish", 60, "非 OPEC 產量增加與高利率壓抑需求", "原油微跌舒緩物流成本", "OPEC 延長額外減產", "全球衰退疑慮加劇", 35, "2026-08-14"),
        ("CRUDE_OIL", "ENERGY", "6M", "$72–78 / 桶", "Bearish", 60, "全球原油供給過剩預期增強", "中長期化工原料與淋膜 PE 成本走降", "產油國突發中斷", "電動車滲透與需求放緩", 50, "2026-08-14"),

        ("COAL_TW", "ENERGY", "1M", "USD 135–142 / 噸", "Neutral", 70, "澳洲 Newcastle 供應充裕，台廠 SRF 生質能替代率逾 40%", "每噸造紙蒸氣成本鎖定於 NT$720–780", "澳洲極端氣候干擾港口裝載", "亞洲電廠補庫告一段落", 25, "2026-08-14"),
        ("COAL_TW", "ENERGY", "3M", "USD 130–138 / 噸", "Bearish", 65, "秋季亞太電力需求回落，進口煤到岸價走軟", "台廠汽電共生效益擴大，毛利修復 30–50 bps", "冬季提前儲煤拉動煤價", "印尼與澳洲產量齊放", 40, "2026-08-14"),
        ("COAL_TW", "ENERGY", "6M", "USD 125–135 / 噸", "Bearish", 60, "綠能與生質鍋爐商轉，外部燃煤依賴下降", "造紙能源成本年減 5–8%", "冬季寒冬拉動熱電需求", "碳費開徵加速生質能替代", 60, "2026-08-14"),

        ("COAL_CN", "ENERGY", "1M", "RMB 830–860 / 噸", "Neutral", 70, "迎峰度夏尾聲，長協煤發揮壓艙石作用", "秦皇島 5500 大卡平倉價穩健，工紙自備電廠盈利穩定", "安全檢查升級限制主產區產能", "水電發電量大增替代火電", 30, "2026-08-14"),
        ("COAL_CN", "ENERGY", "3M", "RMB 800–840 / 噸", "Bearish", 65, "坑口產能充沛，GB 31825-2024 能耗雙控淘汰高耗能小廠", "工紙大廠 Raw Material Spread 擴大", "冬儲煤提前啟動", "工業用電增長放緩", 45, "2026-08-14"),
        ("COAL_CN", "ENERGY", "6M", "RMB 780–820 / 噸", "Bearish", 60, "煤炭供給寬鬆，熱電每噸紙耗成本降 15–20 元", "龍頭造紙廠毛利率重回 16–18% 軌道", "北方供暖季極寒天氣", "煤炭產能進一步集中", 65, "2026-08-14"),

        ("COAL_JP", "ENERGY", "1M", "USD 140–148 / 噸", "Neutral", 65, "日本進口煤 CIF 穩定，日圓走升對沖能源支出", "日本造紙業電價成本高檔企穩", "日圓重新貶值推高進口日幣計價", "核電重啟舒緩電網壓力", 20, "2026-08-14"),
        ("COAL_JP", "ENERGY", "3M", "USD 135–142 / 噸", "Neutral", 60, "JEPX 電力批發價平穩，特種紙維持高報價", "日本製紙/大王製紙下半年獲利轉正", "日圓震盪加劇", "電力長約談判順暢", 30, "2026-08-14"),
        ("COAL_JP", "ENERGY", "6M", "USD 130–138 / 噸", "Bearish", 60, "日本綠色能源轉型與紙廠木質生質發電量產", "日廠海外紙板競爭力修復", "全球能源地緣危機", "節能技術全面導入", 45, "2026-08-14"),

        ("FREIGHT_SCFI", "FREIGHT", "1M", "3,100–3,300 點", "Neutral", 60, "美線旺季出貨強勁，紅海繞航持續消耗運力", "美廢 FAS-CIF 價差維持 $35–45/噸，出口紙箱運費高企", "港口罷工風險推升運價破 3,600", "外貿訂單提早放緩", 25, "2026-08-14"),
        ("FREIGHT_SCFI", "FREIGHT", "3M", "2,700–3,000 點", "Bearish", 70, "歐美返校與年終節慶拉貨結束，新船集中交付", "海運費回落降低美廢進口與亞洲紙品外銷成本", "紅海局勢進一步惡化", "歐美庫存充裕拉貨斷崖", 40, "2026-08-14"),
        ("FREIGHT_SCFI", "FREIGHT", "6M", "2,200–2,600 點", "Bearish", 75, "全球貨櫃航運運力增長 8%，航商價格戰", "台廠與亞洲巨頭外銷運費下降 20–30%，利好出海", "地緣衝突外溢至波斯灣", "全球貿易常態化", 60, "2026-08-14"),

        ("NBSK", "PULP", "1M", "RMB 4,750–4,880 ($663–681)", "Bullish", 75, "4,780 元 ($668) 築底，長短纖價差 433 元 ($61) 終止替代", "針葉漿價格止跌，買盤剛性回流", "智利/北美大型漿廠突發停機", "下游開工率不及預期", 40, "2026-08-14"),
        ("NBSK", "PULP", "3M", "RMB 4,850–5,100 ($677–712)", "Bullish", 70, "金九銀十傳統旺季需求拉動，港口去庫存加速", "漿價溫和反彈，推動文化紙與特種紙漲價落地", "全球補庫週期超預期共振", "宏觀景氣復甦遲緩", 60, "2026-08-14"),
        ("NBSK", "PULP", "6M", "RMB 5,000–5,300 ($698–740)", "Bullish", 65, "歐美紙板與特種紙需求回溫，針葉漿供應結構偏緊", "華紙與造紙廠原料庫存增值，毛利顯著提升", "俄羅斯針葉漿進口受阻", "新開產能超預期釋放", 80, "2026-08-14"),

        ("BHKP", "PULP", "1M", "RMB 4,300–4,400 ($600–614)", "Neutral", 70, "Suzano Cerrado 255 萬噸放量，現貨支撐力道強", "短纖在 $600/噸附近打底盤整", "巴西港口物流塞港", "南美新產線超額低價拋售", 20, "2026-08-14"),
        ("BHKP", "PULP", "3M", "RMB 4,250–4,450 ($593–621)", "Neutral", 60, "全球短纖供應充沛，新產能吸收期壓抑大幅反彈", "家紙與生活用紙原料成本平穩受控", "亞洲下游家紙需求爆發", "歐美紙廠開工低迷", 30, "2026-08-14"),
        ("BHKP", "PULP", "6M", "RMB 4,300–4,550 ($600–635)", "Neutral", 55, "低成本優勢確立，全球短纖供需重回新平衡", "亞洲漿廠採購成本穩定，盈利彈性優於長纖", "環保法規迫使舊產線關停", "新興市場需求疲軟", 40, "2026-08-14"),

        ("CONTAINERBOARD", "PAPER", "1M", "+$80–140/美噸 (美) / +10% (台)", "Bullish", 80, "PCA/IP/SW 9/1 調價進入倒數，正隆平陽三期投產放量", "台廠與美廠利差達 $720 歷史高位，毛利大幅跳升", "北美提價執行率達 100%", "下游包裝廠抵制提價", 85, "2026-08-14"),
        ("CONTAINERBOARD", "PAPER", "3M", "高檔堅挺 (亞洲 +$30–50/噸)", "Bullish", 75, "金九銀十電商與外銷包裝旺季，亞洲工紙搶單效應", "榮成與正隆下半年獲利創年內高峰", "反內卷政策持續推升原紙價", "終端消費不如預期", 110, "2026-08-14"),
        ("CONTAINERBOARD", "PAPER", "6M", "維持高位震盪", "Bullish", 70, "歐美舊產能永久退出 390 萬噸，全球工紙供給偏緊", "工紙業進入景氣上行週期，台灣四大廠營運爆發", "全球新產能開出延遲", "關稅貿易壁壘加劇", 130, "2026-08-14"),

        ("WHITECARD", "PAPER", "1M", "RMB +100–200 / 噸", "Bullish", 75, "玖龍/金光五大廠 8/1 追加提價，GB 31825 能耗限額倒逼", "進口白卡與國產價差縮至 50 元，封鎖低價傾銷", "龍頭紙廠提價全數落地", "下游彩盒廠轉移訂單", 50, "2026-08-14"),
        ("WHITECARD", "PAPER", "3M", "RMB 4,600–4,850 / 噸", "Bullish", 70, "中秋與節慶食品卡紙包裝剛需爆發", "白卡紙行業利潤全面修復轉正", "食品接觸新規 GB 4806.10 催化換代", "中小廠復產衝擊價格", 75, "2026-08-14"),
        ("WHITECARD", "PAPER", "6M", "RMB 4,700–5,000 / 噸", "Bullish", 65, "無塑防油塗佈卡紙放量，以紙代塑替代效應擴大", "高階食品卡紙供不應求，毛利率突破 20%", "歐美 PPWR 帶動全球出口採購", "替代材質競爭", 90, "2026-08-14"),

        ("CULTURAL", "PAPER", "1M", "RMB 4,800–5,000 / 噸", "Neutral", 65, "秋季教材印製招標支撐底盤，文化紙打底震盪", "華紙雙膠紙出貨平穩，營業利潤打底", "秋季印製需求提前釋放", "出版印量結構性衰退", 15, "2026-08-14"),
        ("CULTURAL", "PAPER", "3M", "RMB 4,900–5,150 / 噸", "Neutral", 60, "低價原料木漿在庫存反映，文化紙毛利微幅修復", "紙廠轉向高階商業印刷與包裝用紙", "木漿反彈推動文化紙跟漲", "數位化進一步侵蝕印量", 30, "2026-08-14"),
        ("CULTURAL", "PAPER", "6M", "RMB 5,000–5,250 / 噸", "Neutral", 55, "文化紙產線轉型特種紙與無塑塗佈紙", "產能結構優化，獲利防禦力增強", "特種紙出口放量", "傳統文化紙持續萎縮", 45, "2026-08-14"),

        ("TISSUE", "PAPER", "1M", "RMB 5,200–5,400 / 噸", "Neutral", 70, "民生消費剛性支撐，低價短纖原料庫存利好毛利", "永豐餘五月花與家紙事業獲利穩健", "通路促銷帶動銷量增長", "同業價格戰加劇", 25, "2026-08-14"),
        ("TISSUE", "PAPER", "3M", "RMB 5,300–5,500 / 噸", "Neutral", 70, "下半年電商購物節補庫，家紙出貨動能升溫", "家紙業務貢獻穩定現金流", "高階保濕紙巾新品放量", "短纖成本超預期反彈", 40, "2026-08-14"),
        ("TISSUE", "PAPER", "6M", "RMB 5,400–5,650 / 噸", "Neutral", 65, "綠色抑菌與無漂白環保家紙滲透率上升", "產品組合升級帶動 ASP 上升", "ESG 品牌認同度提升", "原料價格波動", 55, "2026-08-14")
    ]

    for f in forecasts_seed:
        cursor.execute("""
        INSERT INTO price_forecasts (
            target_item, category, horizon, target_price_range, trend_direction,
            probability_pct, catalysts, scenario_base, scenario_bull, scenario_bear,
            margin_impact_bps, obs_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_item, horizon, obs_date) DO UPDATE SET
            target_price_range=excluded.target_price_range,
            trend_direction=excluded.trend_direction,
            probability_pct=excluded.probability_pct,
            catalysts=excluded.catalysts,
            scenario_base=excluded.scenario_base,
            scenario_bull=excluded.scenario_bull,
            scenario_bear=excluded.scenario_bear,
            margin_impact_bps=excluded.margin_impact_bps,
            updated_at=datetime('now', 'localtime')
        """, f)

    # 寫入包含 50 則業界新聞候選庫 (新增日本北越、シモジマ、スーパーバッグ、ザ・パック、TOPPAN、DNP 與北美 Paper Bag 專屬動向)
    news_seed = [
        # --- 嚴選 12 則 (selected_for_report = 1, status = 'approved') ---
        ("N2026W33_01", "正隆（1904）7 月營收 42.56 億創近 19 個月新高", "TW", "CORPORATE", '["企業","產量","包裝"]', "2026-08-08", "2026-08-12", "經濟日報", "https://money.udn.com/", "正隆 7 月合併營收衝上 42.56 億元（月增 9.74%、年增 22.82%），上半年稅後淨利 16.08 億元（EPS 1.45 元），雙創近 4 年同期新高。核心動力來自越南平陽造紙廠第三期工紙產線（年產能 40 萬噸）於 7 月正式商業運轉放量，使正隆在越南總工紙產能突破 100 萬噸，躍居當地最大之低碳循環造紙基地。此外，國內 5 月發動之 +10% 紙箱價格轉嫁於 7-8 月全面反映，配合竹北與后里廠生質能鍋爐運轉順暢（SRF/RDF 替代率逾 40%），下半年毛利率預估重回 18–20% 之健康軌道。", "high", 1, "approved"),
        ("N2026W33_02", "榮成（1909）前 7 月自結稅前淨利達 4.29 億元轉虧為盈，8/12 重訊暫停交易引發市場關注", "TW", "CORPORATE", '["企業","價格","包裝"]', "2026-08-08", "2026-08-12", "工商時報", "https://ctee.com.tw/", "榮成 7 月單月營收 43.24 億元（年增 20.32%），單月自結稅前盈餘約 1.3 億元，前 7 月累計稅前淨利達 4.29 億元（較去年同期虧損 6.82 億元大幅改善，順利轉虧為盈），每股稅前盈餘 0.33 元。成長主因受惠於中國工紙市場「反內卷」價格拉動與無錫、湖北廠廢紙精準採購成本控制。此外，榮成於 2026-08-12 因重大訊息待公布暫停交易，市場推測與評估控股結構轉型與海外投資布局有關，為工紙三雄後續動向增添戰略想像。", "high", 1, "approved"),
        ("N2026W33_03", "華紙與永豐餘推進生質能與無塑防油卡紙佈局", "TW", "CORPORATE", '["企業","食品包裝","包裝"]', "2026-08-08", "2026-08-12", "中央社", "https://www.cna.com.tw/", "華紙（1905）7 月營收 15.20 億元（月增 0.15%、年增 1.48%），創近 2 個月新高。雖然文化紙下游需求仍處打底調整期，但華紙加速推進二極電析生質能綠電建置，並擴大水性無塑塗佈卡紙「益思漿紙 EASY PAPER」放量，食品接觸認證通過率達 90%。永豐餘（1907）7 月營收 64.51 億元（年增 7.28%），前 7 月累計營收 443.1 億元，特化與消費品事業雙引擎發揮功效，智慧能源與碳管理事業開始產生商轉收益，展現同業中最佳的氣候防禦韌性。", "med", 1, "approved"),
        ("N2026W33_05", "中國五大白卡紙廠集體宣漲 200 元／噸，8 月續推 100 元漲價函", "CN", "PAPER_MILL", '["價格","產量","包裝","食品包裝"]', "2026-08-01", "2026-08-12", "新浪財經", "https://finance.sina.com.cn/", "玖龍紙業、金光 (APP)、晨鳴紙業、太陽紙業、博匯紙業等五大白卡巨頭，繼 7 月 1 日成功實施全系列白卡紙（含銅版卡與食品卡）提價 200 元/噸後，8 月 1 日起玖龍進一步發布第二次漲價函追加 100 元/噸。調價受惠於國家《紙及紙板單位產品能源消耗限額》（GB 31825-2024）淘汰落後中小產線，加上進口白卡與國產白卡價差縮小至 50 元/噸以內，海外傾銷空間被封鎖，紙廠正全力在「金九銀十」傳統旺季前修復毛利。", "high", 1, "approved"),
        ("N2026W33_06", "生意社: 8月10日漂針漿4,783元/噸(USD 668)強預期弱現實打底", "CN", "RAW_MATERIAL", '["價格","原料"]', "2026-08-10", "2026-08-12", "生意社", "https://www.100ppi.com/vane/detail-1053.html", "中國進口針葉漿 8 月現貨均價報 4,783 元人民幣／噸（折合 USD 668／噸），闊葉漿報 4,350 元／噸（折合 USD 607／噸），上期所漂針漿期貨主力結算價收於 4,682 元/噸。目前長短纖現貨價差僅 433 元人民幣／噸（折合 USD 61／噸），遠低於 500 元的長短纖替代門檻。下游紙廠（文化紙與特種紙）停止以短纖替代長纖，買盤剛性回流，顯示木漿價格已進入實質築底階段。", "high", 1, "approved"),
        ("N2026W33_08", "中國工紙反內卷與 GB 31825-2024 能耗雙控約束，廢紙價穩中帶漲", "CN", "REGULATION", '["法規","產業","產量"]', "2026-08-05", "2026-08-12", "卓創資訊", "https://finance.sina.com.cn/", "中國工紙市場受政策「反內卷」與能耗雙控約束，玖龍、山鷹等廢紙收購價調漲 20–30 元/噸，國產廢紙到廠基準價站上 1,978 元人民幣/噸（折合 USD 276/噸）。在廢紙成本低位盤整、工紙原紙價格推升背景下，龍頭造紙廠 Raw Material Spread 顯著擴張，二季度起集體扭虧為盈。", "high", 1, "approved"),
        ("N2026W33_09", "東南亞成為台廠產能與回收纖維料源核心基地", "APAC", "RAW_MATERIAL", '["產業","原料","產量"]', "2026-08-09", "2026-08-12", "Paperluz", "https://paperluz.internal/", "隨正隆平陽三期 40 萬噸工紙產線開出，配合東南亞廢紙 (OCC) 到港成本穩定於 USD 130–135/美噸，台廠在越南與泰國之產能比重顯著提升。東南亞不僅成為美中貿易戰下外銷包裝需求增長最快區域，亦成為台廠採購低成本美廢與歐廢的重要運籌中心。", "high", 1, "approved"),
        ("N2026W33_10", "日本造紙 (Nippon Paper) 熊本震後局部停工，亞太特種紙交期略受影響", "JP", "DOWNTIME", '["產量","產業","印刷"]', "2026-08-02", "2026-08-12", "Nikkei Asia", "https://asia.nikkei.com/", "受到 7 月熊本地震餘震與設備巡檢影響，日本造紙 (Nippon Paper Industries, 3863.T) 八代廠部分特種紙、包裝紙與綠色紙容器產線進行預防性停工維修。雖然公司啟動跨廠調度救援機制，但亞太地區部分高階食品包裝紙與印刷塗佈紙短期交期延長 7–10 天，台灣進口業者需密切注意到貨排程。", "med", 1, "approved"),
        ("N2026W33_11", "歐美與亞洲工紙價差擴至 $180–220/噸，引發外銷搶單效應", "GLOBAL", "LOGISTICS", '["價格","包裝","產業"]', "2026-08-07", "2026-08-12", "上海航運交易所", "https://www.sse.net.cn/", "歐美箱板紙價格因產能關停與提價強勢走高，與亞洲工紙價差擴大至每噸 USD 180–220。配合上海出口集裝箱運價指數 (SCFI) 報 3,276.14 點、美線運價高檔震盪，亞洲工紙巨頭與台廠積極利用價格優勢，擴大對中東、印度與東南亞的外銷出口搶單。", "high", 1, "approved"),
        ("N2026W33_12", "北美箱板紙 9/1 漲價宣告落地倒數：PCA +$140 / IP +$80 / SW +$100", "US", "PAPER_MILL", '["價格","包裝","產量"]', "2026-08-01", "2026-08-12", "Packaging Dive", "https://www.packagingdive.com/", "北美箱板紙賣方市場態勢明確。繼 Packaging Corporation of America (PCA) 宣告史上最大單筆提價 +$140/美噸後，International Paper (+80 美元/美噸) 與 Smurfit Westrock (+100 美元/美噸) 9/1 生效調價進入倒數。配合 IP 關閉 Pine Hill 廠等美洲 390 萬噸永久產能退出，造紙廠 Raw Material Spread 擴張至 $720/美噸以上，獲利彈性創 3 年新高。", "high", 1, "approved"),
        ("N2026W33_13", "歐盟 PPWR 法規 (EU) 2025/40 強制生效：全歐包裝啟用 Design for Recycling", "EU", "REGULATION", '["法規","包裝","食品包裝"]', "2026-08-12", "2026-08-12", "EUR-Lex", "https://eur-lex.europa.eu/", "2026-08-12 歐盟《包裝與包裝廢棄物法規》(PPWR, Regulation (EU) 2025/40) 正式實施。所有銷歐商品之外銷包裝強制落入設計可回收性（Design for Recycling, DfR）與數位產品護照（DPP）稽核。配合 (EU) 2024/3190 雙酚 A 禁令已屆滿與 PFHxA 限制即將於 10/11 適用，去 PFAS 食品包裝與無塑塗佈成為不可逆之採購剛需。", "high", 1, "approved"),
        ("N2026W33_14", "歐美白紙板 / SBS 迎來 8–9 月連番調漲 4–6%", "EU", "PAPER_MILL", '["價格","包裝","食品包裝"]', "2026-08-05", "2026-08-12", "Fastmarkets", "https://www.fastmarkets.com/", "Smurfit Westrock（8/10 生效）、Sappi North America（8/20 生效）與 Metsä Board（9/1 生效）連番宣告調升折疊紙盒級 SBS 與 FBB 白紙板價格 4–6%。歐洲箱板紙 Q2 累計已上漲 +€120/噸，多數紙種幾乎售罄，全球高階彩盒、化妝品與食品卡紙採購成本顯著走揚。", "high", 1, "approved"),

        # --- 新增 CORE 日本紙廠、紙袋會社 (The Pack, Super Bag, Shimojima, Hokuetsu, TOPPAN, DNP) 與北美 Paper Bag 備戰新聞 (selected_for_report = 0, status = 'candidate') ---
        ("N2026W33_JP_01", "ザ・パック (The Pack 3950.T) 發布最新永續紙袋與牛皮紙袋出貨月報", "JP", "PAPER_BAG", '["紙袋","包裝","食品包裝","企業"]', "2026-08-10", "2026-08-12", "The Pack IR", "https://www.thepack.co.jp/", "日本第一大紙袋製造商ザ・パック受惠於百貨公司與餐飲外帶紙袋需求強勁，強化手提紙袋與全紙質牛皮紙袋市佔", "high", 0, "candidate"),
        ("N2026W33_JP_02", "シモジマ (Shimojima 7482.T) 擴大環保牛皮紙袋與店舖包裝資材物流供應", "JP", "PACKAGING", '["包裝","紙袋","企業"]', "2026-08-09", "2026-08-12", "Shimojima IR", "https://www.shimojima.co.jp/", "日本包裝專門商社シモジマ因應禁塑法規，提供零售業者多規格牛皮紙袋與防油紙餐袋", "med", 0, "candidate"),
        ("N2026W33_JP_03", "スーパーバッグ (Super Bag 3945.T) 發表高強度防潮牛皮購物紙袋專利", "JP", "PAPER_BAG", '["紙袋","包裝","食品包裝"]', "2026-08-08", "2026-08-12", "Super Bag IR", "https://www.superbag.co.jp/", "研發多層強化紙柄與水性淋膜紙袋，搶攻日本與外銷連鎖餐飲紙袋訂單", "med", 0, "candidate"),
        ("N2026W33_JP_04", "北越 Corporation (Hokuetsu 3865.T) 提升新潟廠高級白紙板與卡紙稼動率", "JP", "PAPER_MILL", '["產量","包裝","企業"]', "2026-08-07", "2026-08-12", "Hokuetsu IR", "https://www.hokuetsucorp.com/", "北越高階白紙板與塗佈卡紙出貨順暢，受惠於歐美進口卡紙價格高企", "med", 0, "candidate"),
        ("N2026W33_JP_05", "TOPPAN (凸版印刷 7911.T) 與 DNP (大日本印刷 7912.T) 加速綠色包裝與無塑紙容器研發", "JP", "PRINTING", '["印刷","包裝","食品包裝","企業"]', "2026-08-11", "2026-08-12", "TOPPAN IR", "https://www.holdings.toppan.com/", "日本兩大印刷巨頭轉向高障礙阻隔紙材與數位印刷，因應歐盟與日本 Packaging Regulation", "high", 0, "candidate"),
        ("N2026W33_US_01", "北美牛皮紙袋 (Kraft Paper Bag) 受各州禁塑法帶動需求年增 5.2%", "US", "PAPER_BAG", '["紙袋","包裝","法規"]', "2026-08-10", "2026-08-12", "Novolex News", "https://novolex.com/", "Novolex 與 Duro Bag 報告指出全美零售與快餐紙袋訂單強勁，未漂白牛皮紙 (Unbleached Kraft) 價格堅挺", "high", 0, "candidate"),

        # --- 其餘候選庫 28 則 ---
        ("N2026W33_15", "美元兌新台幣收 32.250，台幣升值降低進口木漿成本", "TW", "LOGISTICS", '["價格","原料"]', "2026-08-10", "2026-08-12", "中央銀行", "https://www.cbc.gov.tw/", "台幣升值 2.3 角，外購木漿與美廢台幣成本舒緩", "med", 0, "candidate"),
        ("N2026W33_16", "歐盟 (EU) 2024/3190 雙酚 A 禁令：明文涵蓋印刷油墨與紙類食品包裝", "EU", "REGULATION", '["法規","印刷","食品包裝","包裝"]', "2026-08-05", "2026-08-12", "EUR-Lex", "https://eur-lex.europa.eu/", "雙酚 A (BPA) 禁令過渡期屆滿，食品接觸紙材、油墨與塗料全面禁用", "high", 0, "candidate"),
        ("N2026W33_17", "歐盟 PFHxA 全氟酸限制條款：紙容器防油塗層 10/11 前須完成替代", "EU", "REGULATION", '["法規","食品包裝","包裝"]', "2026-08-08", "2026-08-12", "EUR-Lex", "https://eur-lex.europa.eu/", "全氟化合物限制倒數，淋膜紙杯與防油彩盒加速轉向生物基無塑塗層", "high", 0, "candidate"),
        ("N2026W33_18", "中國 GB 4806.10-2025 食品接觸塗料新規 9/2 正式實施", "CN", "REGULATION", '["法規","食品包裝","印刷"]', "2026-08-08", "2026-08-12", "國家標準委", "https://openstd.samr.gov.cn/", "紙杯紙盒淋膜與印刷塗層全面強制適用，不合規產品禁止上市", "high", 0, "candidate"),
        ("N2026W33_19", "台灣《資源循環推動法》三讀公佈：紙業循環經濟與碳費申報備戰", "TW", "REGULATION", '["法規","產業","包裝"]', "2026-08-05", "2026-08-12", "環境部", "https://www.moenv.gov.tw/", "資源循環專法與首期碳費開徵，高碳洩漏風險紙廠積極提出自主減量計畫", "high", 0, "candidate"),
        ("N2026W33_20", "Suzano Cerrado 255 萬噸短纖產線放量發揮成本優勢", "GLOBAL", "RAW_MATERIAL", '["產量","原料","價格"]', "2026-08-01", "2026-08-12", "Suzano IR", "https://www.sec.gov/", "出口漿平均淨價 $562/噸展現超低現金成本護城河", "med", 0, "candidate"),
        ("N2026W33_21", "日本製紙與王子控股推動包裝與商業印刷用紙綠色轉型", "JP", "INDUSTRY_TREND", '["產業","印刷","包裝"]', "2026-08-09", "2026-08-12", "日本製紙連合會", "https://www.jpa.gr.jp/", "面對出版紙張衰退，轉向高附加價值無塑包裝紙與綠色印刷基材", "med", 0, "candidate"),
        ("N2026W33_22", "玖龍紙業 2026 財年中期淨利 RMB 22.12 億年增 205%", "CN", "CORPORATE", '["企業","價格","產量"]', "2026-08-03", "2026-08-12", "新浪財經", "https://finance.sina.com.cn/", "受惠於廢紙成本低檔與白卡/工紙漲價利差擴張", "med", 0, "candidate"),
        ("N2026W33_23", "王子控股 (Oji Holdings) 宣布擴大馬來西亞與越南包裝紙箱佈局", "JP", "CORPORATE", '["企業","包裝","產量"]', "2026-08-07", "2026-08-12", "Nikkei Asia", "https://asia.nikkei.com/", "強化東南亞包裝製造據點，應對供應鏈轉移需求", "med", 0, "candidate"),
        ("N2026W33_24", "大王製紙 (Daio Paper) 調整日本國內衛生紙與家紙牌價", "JP", "PAPER_MILL", '["價格","產業"]', "2026-08-06", "2026-08-12", "Daio Paper IR", "https://www.daio-paper.co.jp/", "吸收原料與物流成本上漲，調升家庭用紙出貨報價 5-8%", "med", 0, "candidate"),
        ("N2026W33_25", "連合製紙 (Rengo) 推出全紙質生鮮避光防潮物流紙箱", "JP", "PACKAGING", '["包裝","食品包裝","印刷"]', "2026-08-08", "2026-08-12", "Rengo IR", "https://www.rengo.co.jp/", "替換塑膠包裝，搶攻歐美冷鏈與農產品外銷市場", "med", 0, "candidate"),
        ("N2026W33_26", "日本消費者廳食品接觸 Positive List 新規推進紙容器界線檢視", "JP", "REGULATION", '["法規","食品包裝"]', "2026-08-04", "2026-08-12", "CAA Japan", "https://www.caa.go.jp/", "明確淋膜聚合物合規邊界，確保進口紙杯安全性", "med", 0, "candidate"),
        ("N2026W33_27", "太陽紙業老撾 30 萬噸漿紙一體化擴建產線順利試運轉", "CN", "PAPER_MILL", '["產量","原料","企業"]', "2026-08-05", "2026-08-12", "太陽紙業 IR", "http://www.sunpapergroup.com/", "自製木漿成本進一步下降，發揮林漿紙一體化優勢", "med", 0, "candidate"),
        ("N2026W33_28", "理文造紙越南後江造紙基地二期 50 萬噸工紙項目啟動", "CN", "PAPER_MILL", '["產量","包裝","企業"]', "2026-08-06", "2026-08-12", "理文造紙 IR", "http://www.leemanpaper.com/", "加碼東南亞包裝紙板產能，搶佔區域外銷份額", "med", 0, "candidate"),
        ("N2026W33_29", "山鷹國際與東南亞回收廢紙大盤簽訂長期 OCC 供應協定", "CN", "RAW_MATERIAL", '["原料","包裝","企業"]', "2026-08-07", "2026-08-12", "山鷹國際 IR", "http://www.shanyingintl.com/", "鎖定低價優質美廢與東南亞廢紙料源", "med", 0, "candidate"),
        ("N2026W33_30", "博匯紙業引進高階水性無塑淋膜設備搶攻食品卡紙市場", "CN", "PACKAGING", '["食品包裝","產量","印刷"]', "2026-08-03", "2026-08-12", "博匯紙業 IR", "http://www.bohui-paper.com/", "因應去 PE 淋膜趨勢，推出環保可降解食品卡紙", "med", 0, "candidate"),
        ("N2026W33_31", "晨鳴紙業壽光廠高階雙膠紙與銅版紙節能降碳升級完成", "CN", "PAPER_MILL", '["產量","印刷","企業"]', "2026-08-04", "2026-08-12", "晨鳴紙業 IR", "http://www.chenmingpaper.com/", "符合 GB 31825 能耗限定值要求，提速高階文化紙產能", "low", 0, "candidate"),
        ("N2026W33_32", "台灣工業局與造紙公會推動紙廠自發綠電與二極電析技術論壇", "TW", "INDUSTRY_TREND", '["產業","法規","企業"]', "2026-08-09", "2026-08-12", "經濟部", "https://www.moea.gov.tw/", "協助四大紙廠轉型低碳循環經濟與綠電自給率", "med", 0, "candidate"),
        ("N2026W33_33", "台灣大盤廢紙收購價維持 4,200 元/噸，紙廠庫存維持 35 天健康位階", "TW", "RAW_MATERIAL", '["價格","原料","包裝"]', "2026-08-11", "2026-08-12", "Paperluz Data", "https://paperluz.internal/", "國內廢紙供需平穩，工紙廠原料到港成本可控", "med", 0, "candidate"),
        ("N2026W33_34", "永豐餘旗下申豐特化生質膠乳通過歐盟食品接觸材料認證", "TW", "CORPORATE", '["食品包裝","印刷","企業"]', "2026-08-07", "2026-08-12", "永豐餘 IR", "https://www.yfy.com/", "拓展無毒塗布材料海外供應鏈，挹注高毛利獲利", "med", 0, "candidate"),
        ("N2026W33_35", "榮成無錫廠導入高效率廢水沼氣發電，單噸紙碳足跡降低 12%", "TW", "CORPORATE", '["產業","產量","企業"]', "2026-08-06", "2026-08-12", "榮成 IR", "https://www.longchenpaper.com/", "減碳效益顯著，應對中國碳市場履約需求", "med", 0, "candidate"),
        ("N2026W33_36", "Graphic Packaging (GPI) 美國新一代無塑麥當勞冷飲紙杯放量出貨", "US", "PACKAGING", '["食品包裝","包裝","印刷"]', "2026-08-08", "2026-08-12", "Packaging Dive", "https://www.packagingdive.com/", "替代傳統 PE 淋膜紙杯，加速連鎖餐飲無塑化", "high", 0, "candidate"),
        ("N2026W33_37", "Stora Enso 芬蘭 Oulu 廠 55 萬噸高階消費紙板產線啟動商業交付", "EU", "PAPER_MILL", '["產量","包裝","食品包裝"]', "2026-08-05", "2026-08-12", "Stora Enso IR", "https://www.storaenso.com/", "專注歐洲高階折疊盒與生鮮食品包裝需求", "high", 0, "candidate"),
        ("N2026W33_38", "UPM 烏拉圭 Paso de los Toros 210 萬噸桉木漿廠稼動率達 95%", "EU", "RAW_MATERIAL", '["產量","原料","企業"]', "2026-08-04", "2026-08-12", "UPM IR", "https://www.upm.com/", "全球短纖供給充沛，現金成本極具競爭優勢", "med", 0, "candidate"),
        ("N2026W33_39", "Mondi 完成對德國 Schumacher Packaging 收購案，鞏固歐洲紙箱龍頭", "EU", "CORPORATE", '["企業","包裝","產量"]', "2026-08-06", "2026-08-12", "Mondi IR", "https://www.mondigroup.com/", "整合德國瓦楞紙箱產能，提升歐洲供應鏈佔有率", "med", 0, "candidate"),
        ("N2026W33_40", "智利 Arauco 發表 MAPA 專案新產能品質報告，亞洲漂針漿報價持平", "GLOBAL", "RAW_MATERIAL", '["原料","價格","產量"]', "2026-08-07", "2026-08-12", "Arauco IR", "https://www.arauco.com/", "智利漿廠月度外盤定價穩健，亞洲到岸價築底", "med", 0, "candidate"),
        ("N2026W33_41", "巴西 Klabin Puma II 廠塗佈牛皮卡紙與 Kraftliner 出口量創季度新高", "GLOBAL", "PAPER_MILL", '["產量","包裝","企業"]', "2026-08-05", "2026-08-12", "Klabin IR", "https://ri.klabin.com.br/", "南美紙板外銷亞洲與歐洲，展現強勁原料優勢", "med", 0, "candidate"),
        ("N2026W33_42", "Mercer International 德國長纖漿廠歲修完成，NBKP 現貨市場供給平穩", "GLOBAL", "RAW_MATERIAL", '["產量","原料","價格"]', "2026-08-06", "2026-08-12", "Mercer IR", "https://www.mercerint.com/", "歐洲針葉漿產能修復，全球長纖供需平衡", "low", 0, "candidate"),

        # --- 2026-08-18 深度產業調研入庫新聞 (TW, US, CN, EU, JP, GLOBAL, FREIGHT & ENERGY) ---
        ("N2026W33_TW_01", "榮成（1909）8/12 宣布轉型投資控股公司，工紙紙箱事業分割讓與「榮成低碳紙箱」", "TW", "CORPORATE", '["企業","價格","包裝","產業"]', "2026-08-12", "2026-08-18", "公開資訊觀測站/工商時報", "https://ctee.com.tw/", "榮成於 2026 年 8 月 12 日暫停交易並召開重訊記者會，宣布董事會通過以分割方式轉型為「榮成投資控股股份有限公司」，將台灣工業用紙與紙箱事業相關資產、負債及營運概括讓與 100% 持股子公司「榮成低碳紙箱股份有限公司」，分割基準日暫訂為 2027 年 1 月 4 日。公司 8 月 13 日恢復交易。榮成第二季合併營收 134.87 億元（年增 21%），稅後淨利 2.70 億元（EPS 0.21 元），前 7 月自結稅前獲利達 4.29 億元成功轉虧為盈，受惠中國市場反內卷提價及低成本廢紙採購優勢。", "high", 1, "approved"),
        ("N2026W33_TW_02", "正隆（1904）7 月營收 42.56 億創 19 個月新高，越南平陽三期 40 萬噸工紙全面商業運轉", "TW", "CORPORATE", '["企業","產量","包裝","價格"]', "2026-08-08", "2026-08-18", "經濟日報/公開資訊觀測站", "https://money.udn.com/", "正隆 7 月合併營收衝上 42.56 億元（月增 9.75%、年增 22.82%），上半年稅後淨利 16.08 億元（EPS 1.45 元，年增約 52 倍），創近 4 年同期新高。核心驅動力為越南平陽造紙廠第三期工紙產線（年產能 40 萬噸）於 7 月正式商轉放量，使正隆在越南總工紙產能突破 100 萬噸，成為當地最大之低碳循環造紙基地。此外，國內 5 月發動之 +10% 紙箱價格轉嫁已全面反映，配合生質能鍋爐運轉順暢（SRF 替代率逾 40%），下半年毛利率可望維持在 18–20% 高檔區間。", "high", 1, "approved"),
        ("N2026W33_TW_03", "永豐餘（1907）上半年稅後淨利 7.79 億元由虧轉盈創 5 年同期新高，元太投資收益貢獻 10.91 億", "TW", "CORPORATE", '["企業","包裝","產業","食品包裝"]', "2026-08-11", "2026-08-18", "中央社/鉅亨網", "https://www.cna.com.tw/", "永豐餘 2026 年第二季合併營收 198.95 億元（年增 9.4%），稅後淨利 5.71 億元；累計上半年營收 378.59 億元，稅後淨利 7.79 億元（EPS 0.47 元），由虧轉盈創近 5 年同期新高。獲利大幅成長主因工紙紙器事業群虧損大幅收斂、越南紙器需求強勁，加上權益法認列轉投資元太科技投資收益達 10.91 億元（年增 22.6%）。公司持續推進「氣候科技產業」轉型，深化生質能源與智慧碳管理佈局。", "high", 1, "approved"),
        ("N2026W33_TW_04", "華紙（1905）第三季啟動減產保價策略回收現金，全力擴展非氟防油紙與生質綠電", "TW", "RAW_MATERIAL", '["原料","企業","食品包裝","法規"]', "2026-08-11", "2026-08-18", "工商時報", "https://ctee.com.tw/", "華紙 2026 年上半年合併營收 90.8 億元（年減 5.1%），歸屬母公司稅後淨損 5.79 億元（每股虧損 0.52 元）。受國際木片成本居高不下與漿價低迷夾擊，華紙第三季實施「減產保價」策略至 10 月以回收營運現金。同時，華紙加速轉型，非氟防油紙、水性無塑塗佈卡紙「益思漿紙 EASY PAPER」食品接觸認證通過率達 90%，並推進花蓮廠二極電析生質能綠電商轉，預期第四季漿價反彈後營運重回成長軌道。", "high", 1, "approved"),
        ("N2026W33_TW_05", "台灣環境部研商碳費徵收與《資源循環推動法》，四大紙廠提自主減量計畫備戰", "TW", "REGULATION", '["法規","產業","企業"]', "2026-08-10", "2026-08-18", "環境部/經濟日報", "https://www.moenv.gov.tw/", "台灣環境部召開碳費徵收費率審議與《資源循環推動法》座談會，明定高碳洩漏風險行業過渡配套。正隆、永豐餘、榮成、華紙等造紙大廠積極提出自主減量計畫（SBTi 與生質鍋爐替代），廠區 SRF / RDF 替代煤炭比率超過 40%，以爭取優惠碳費費率（每噸約 100 元新台幣），加速綠色轉型與能耗優化。", "med", 0, "approved"),
        ("N2026W33_TW_06", "台灣廢紙收購價維持 4,200 元/噸，造紙廠原料庫存天數維持 35 天健康位階", "TW", "RAW_MATERIAL", '["價格","原料","包裝"]', "2026-08-11", "2026-08-18", "Paperluz Data/台灣造紙公會", "https://paperluz.internal/", "國內廢紙大盤到廠收購基準價維持於 4,200 元新台幣／公噸。各大工紙廠國內廢紙與進口美廢 (OCC) 採購調度順暢，原料庫存天數維持在 35 天之健康安全位階。原料成本穩定配合工紙成品價格上調，台灣紙廠 Raw Material Spread 維持穩健盈利結構。", "med", 0, "approved"),
        ("N2026W33_US_02", "北美三大工紙巨頭 PCA (+140 美元)、Smurfit (+100 美元)、IP (+80 美元) 9/1 調價進入生效倒數", "US", "PAPER_MILL", '["價格","包裝","產量","企業"]', "2026-08-05", "2026-08-18", "Packaging Dive", "https://www.packagingdive.com/", "北美箱板紙進入賣方市場。繼 Packaging Corporation of America (PCA) 宣告史上最大單筆提價 +$140/美噸後，International Paper (+80 美元/美噸) 與 Smurfit Westrock (+100 美元/美噸) 9/1 生效調價進入最後 14 天倒數。這是北美紙廠在 2026 年發動的第三輪漲價（H1 累計已漲 +$100/噸）。紙廠表示北美自 2025 年 2 月至 2026 年 3 月已永久關閉 390 萬噸工紙產能，供給紀律與高稼動率支撐漲價動能。", "high", 1, "approved"),
        ("N2026W33_US_03", "國際瓦楞紙箱製造商協會 (AICC) 公開質疑北美紙廠密集漲價，指前三大巨頭掌握 63% 市佔寡占定價", "US", "PACKAGING", '["包裝","價格","產業","企業"]', "2026-08-08", "2026-08-18", "AICC Box / Packaging Dive", "https://www.packagingdive.com/", "國際瓦楞紙箱製造商協會 (AICC) 對北美三大造紙巨頭（PCA、Smurfit Westrock、IP）在 5 個月內密集實施三輪調價公開表達強烈反對與質疑。AICC 指出，當前終端紙箱需求並未顯著爆發，但三大巨頭合計掌握全美 63% 箱板紙產能，利用產能集中度與永久關廠創造人為緊缺，推升美國箱板紙原料利差 (Raw Material Spread) 突破 $720/美噸歷史高點，下游獨立紙箱廠正面臨巨大的轉嫁壓力。", "high", 1, "approved"),
        ("N2026W33_US_04", "美國 11 號 OCC 出口美東 FAS 報 $132–135/噸，美西 FAS 報 $130–133/噸窄幅盤整", "US", "RAW_MATERIAL", '["價格","原料","包裝"]', "2026-08-12", "2026-08-18", "Fastmarkets RISI", "https://www.fastmarkets.com/", "美國 11 號舊瓦楞紙箱廢紙 (OCC #11) 8 月出口價格美東紐約/紐澤西港口 FAS 報 USD 132–135/美噸，美西洛杉磯/長堤港口 FAS 報 USD 130–133/美噸。高等級雙分選 DSOCC #12 維持 USD 140–145/美噸。受紅海繞航與美線貨櫃海運費高企影響，亞洲造紙廠美廢到港 CIF 成本維持在 $170–180/噸高檔，支撐亞洲廢紙收購行情底線。", "med", 0, "approved"),
        ("N2026W33_US_05", "北美牛皮紙袋 (Kraft Paper Bag) 受各州禁塑法帶動需求年增 5.2%，未漂白牛皮紙價格堅挺", "US", "PAPER_BAG", '["紙袋","包裝","法規","價格"]', "2026-08-10", "2026-08-18", "Novolex News / Fastmarkets", "https://novolex.com/", "Novolex、Duro Bag 等北美紙袋龍頭出貨報告指出，加州、紐約州及全美超過 12 個州嚴格實施零售與外帶塑膠袋禁令，帶動全美牛皮紙袋 (Kraft Paper Bags) 需求年增 5.2%。未漂白牛皮紙 (Unbleached Kraft Paper) 牌價每噸維持在 $880–920 美元高檔堅挺，包裝與快餐連鎖品牌加速以多層高強度牛皮紙袋替代塑膠提袋。", "high", 0, "approved"),
        ("N2026W33_US_06", "Graphic Packaging (GPI) 與麥當勞合作新一代無塑冷飲紙杯出貨量突破 1 億只", "US", "PACKAGING", '["食品包裝","包裝","印刷","企業"]', "2026-08-08", "2026-08-18", "Packaging Dive", "https://www.packagingdive.com/", "全球食品包裝巨頭 Graphic Packaging International (GPI) 宣布與麥當勞及大型連鎖餐飲合作之水性無塑塗佈冷飲紙杯累計出貨量突破 1 億只。該款紙杯完全淘汰傳統 PE 淋膜，符合 FDA 與歐盟無氟 (PFAS-free) 嚴苛標準，可直接進入常規廢紙回收循環系統，標誌著北美快餐包裝綠色轉型邁入規模化商業落地階段。", "high", 0, "approved"),
        ("N2026W33_CN_01", "中國五大白卡紙巨頭 8 月發布二次漲價函追加 100 元/噸，金九銀十備貨啟動", "CN", "PAPER_MILL", '["價格","包裝","產量","食品包裝"]', "2026-08-01", "2026-08-18", "新浪財經/卓創資訊", "https://finance.sina.com.cn/", "玖龍紙業、金光集團 (APP)、博匯紙業、太陽紙業、晨鳴紙業等五大白卡巨頭，繼 7 月 1 日成功實施全系列白卡紙（含銅版卡與食品卡）提價 200 元/噸後，8 月 1 日起進一步發布第二次漲價函追加 100 元/噸。調價受惠於下游中秋禮盒與下半年節慶包裝剛需備貨啟動，且進口白卡與國產價差縮小至 50 元/噸以內，低價傾銷窗口關閉，紙廠毛利正全速修復至 15% 以上。", "high", 1, "approved"),
        ("N2026W33_CN_02", "上期所漂針漿期貨主力結算價 4,682 元/噸，長短纖現貨價差 310–433 元築底確立", "CN", "RAW_MATERIAL", '["價格","原料"]', "2026-08-10", "2026-08-18", "上海期貨交易所/生意社", "https://www.shfe.com.cn/", "上海期貨交易所漂針漿期貨 (SHFE SP) 主力合約結算價收於 4,682 元人民幣/噸，現貨針葉漿均價報 4,783 元/噸（折合 USD 668/噸），闊葉漿報 4,350 元/噸（折合 USD 607/噸）。目前長短纖現貨價差僅 310–433 元/噸，遠低於 500 元短纖替代臨界點。文化紙與特種紙廠全面停止以短纖替代長纖，買盤剛性回流，顯示國際木漿價格已確立底部支撐。", "high", 1, "approved"),
        ("N2026W33_CN_03", "中國實施 GB 31825-2024 能耗雙控與工紙「反內卷」，推動造紙毛利全面修復", "CN", "REGULATION", '["法規","產業","產量","包裝"]', "2026-08-05", "2026-08-18", "中國造紙協會/卓創資訊", "http://www.chinappi.org/", "中國國家標準《紙及紙板單位產品能源消耗限額》（GB 31825-2024）強制執行，針對高耗能中小產線進行嚴格限電與能耗約束。在政策引導「反內卷」與產能出清背景下，玖龍、山鷹等廢紙收購價穩步調漲 20–30 元/噸，國產廢紙基準價站上 1,978 元人民幣/噸。瓦楞紙與箱板紙原紙報價維持堅挺，大型紙企 Raw Material Spread 擴大，二季度起集體扭虧為盈。", "high", 1, "approved"),
        ("N2026W33_CN_04", "中國 GB 4806.10-2025 食品接觸塗料新規將於 9/2 正式實施，加速食品紙容器合規換代", "CN", "REGULATION", '["法規","食品包裝","印刷"]', "2026-08-08", "2026-08-18", "國家標準委/食品夥伴網", "https://openstd.samr.gov.cn/", "國家市場監督管理總局與衛健委聯合發布之《食品安全國家標準 食品接觸用塗料及塗層》（GB 4806.10-2025）將於 2026 年 9 月 2 日正式生效。新規對紙杯、紙餐盒及食品包裝紙內壁塗層的有害物質遷移限量（如雙酚 A、重金屬、特定單體）實施嚴格正面清單管制，促使國內食品包裝廠加速轉向水性無塑塗層與生物基防油材料。", "high", 0, "approved"),
        ("N2026W33_CN_05", "太陽紙業老撾 30 萬噸林漿紙一體化產線全速運轉，自製化學漿展現成本護城河", "CN", "PAPER_MILL", '["產量","原料","企業"]', "2026-08-05", "2026-08-18", "太陽紙業 IR/新浪財經", "http://www.sunpapergroup.com/", "太陽紙業老撾基地年產 30 萬噸化學木漿擴產項目進入全面商業運轉，林漿紙一體化佈局顯著降低木片採購與進口漿依賴。配合國內高階文化紙與生活用紙產能放量，太陽紙業單噸紙綜合成本較同業低約 150–200 元人民幣，在漿價築底期展現強勁防禦韌性與毛利率優勢。", "med", 0, "approved"),
        ("N2026W33_EU_01", "歐盟《包裝與包裝廢棄物法規》(PPWR, (EU) 2025/40) 2026-08-12 正式強制生效", "EU", "REGULATION", '["法規","包裝","食品包裝"]', "2026-08-12", "2026-08-18", "EUR-Lex / European Commission", "https://eur-lex.europa.eu/", "2026 年 8 月 12 日，歐盟《包裝與包裝廢棄物法規》(PPWR, Regulation (EU) 2025/40) 正式實施，全體銷歐商品外銷包裝強制落入設計可回收性（Design for Recycling, DfR）與數位產品護照（DPP）稽核範圍。此法規為直接適用的歐盟法，無需各成員國個別立法轉置，標誌著全球外銷包裝進入綠色可回收標準化時代。", "high", 1, "approved"),
        ("N2026W33_EU_02", "歐盟 PPWR 嚴格實施食品接觸包裝 PFAS 限制：單一非聚合物 25ppb、全氟總量 50ppm 門檻", "EU", "REGULATION", '["法規","食品包裝","包裝"]', "2026-08-12", "2026-08-18", "EUR-Lex / ECHA", "https://eur-lex.europa.eu/", "依據 PPWR 第 5 條第 5 項，歐盟對食品接觸紙包裝實施嚴格 PFAS 濃度限制：單一非聚合物 PFAS 不得超過 25 ppb、總非聚合物 PFAS 不得超過 250 ppb、全氟總含量上限為 50 ppm (50 mg/kg)。進口商與包裝業者必須提供合格實驗室檢驗報告與 Annex VII 技術文檔，未合規包裝嚴禁在歐盟境內銷售，去 PFAS 防油塗層迎來爆發式替代潮。", "high", 1, "approved"),
        ("N2026W33_EU_03", "Smurfit Westrock 歐洲箱板紙 Q2 累計調漲 +€120/公噸，多數折疊盒與原生紙種售罄", "EU", "PAPER_MILL", '["價格","包裝","產量","企業"]', "2026-08-05", "2026-08-18", "Fastmarkets / Smurfit Westrock IR", "https://www.smurfitwestrock.com/", "全球最大紙箱包裝集團 Smurfit Westrock 報告指出，歐洲箱板紙與包裝用紙在 2026 年第二季累計實施 +€120/公噸漲價，多數紙廠原生纖維與折疊盒卡紙產能已被預訂一空。受歐洲能源成本結構與環保法規退出產能影響，歐洲工紙供應呈現結構性偏緊，推升區域包裝紙板成交價格維持高位。", "high", 1, "approved"),
        ("N2026W33_EU_04", "Mondi 完成收購德國 Schumacher Packaging，鞏固中歐瓦楞紙箱與食品紙袋霸主地位", "EU", "CORPORATE", '["企業","包裝","紙袋","產量"]', "2026-08-06", "2026-08-18", "Mondi Group IR", "https://www.mondigroup.com/", "歐洲包裝與特種紙巨頭 Mondi 宣布順利完成對德國 Schumacher Packaging 之收購案。該收購案整合了德國、波蘭及中歐地區 7 座先進瓦楞紙器廠與 2 座固廢再生紙板廠，使 Mondi 在歐洲牛皮紙袋、電商瓦楞紙盒及食品冷鏈紙包裝之市佔率進一步擴大，提升跨國供應鏈綜效。", "med", 0, "approved"),
        ("N2026W33_EU_05", "Stora Enso 芬蘭 Oulu 廠 55 萬噸高階消費紙板產線啟動商業交付", "EU", "PAPER_MILL", '["產量","包裝","食品包裝","企業"]', "2026-08-05", "2026-08-18", "Stora Enso IR", "https://www.storaenso.com/", "北歐林漿紙巨頭 Stora Enso 芬蘭 Oulu 廠耗資 10 億歐元轉型之 55 萬噸高級折疊盒紙板 (FBB) 與塗佈牛皮紙板 (CUK) 產線正式啟動商業訂單交付。該產線專門供應歐美高級冷凍食品、化妝品與無塑紙容器，提供高阻隔、可回收之原生纖維包裝解決方案。", "high", 0, "approved"),
        ("N2026W33_JP_06", "王子控股 (Oji Holdings) 與日本製紙 (Nippon Paper) 推進綠色包裝與水性無塑塗佈紙轉型", "JP", "INDUSTRY_TREND", '["產業","包裝","印刷","食品包裝","企業"]', "2026-08-09", "2026-08-18", "日本製紙連合會 / Nikkei Asia", "https://www.jpa.gr.jp/", "日本製紙連合會最新統計顯示，日本傳統商業印刷與出版用紙需求持續呈現年減 4–6% 態勢。王子控股 (Oji) 與日本製紙 (Nippon Paper) 加速產能結構調整，關閉或改造老舊新聞紙機，將產能轉移至水性高阻隔無塑塗佈紙「SHIELDPLUS」與環保外帶紙容器，全面對接便利商店與外銷綠色包裝剛需。", "high", 0, "approved"),
        ("N2026W33_JP_07", "日本製紙八代廠因熊本地震餘震巡檢預防性停工維修，亞太高階食品塗佈紙交期延長 7–10 天", "JP", "DOWNTIME", '["產量","印刷","食品包裝","企業"]', "2026-08-02", "2026-08-18", "Nikkei Asia / Nippon Paper IR", "https://asia.nikkei.com/", "日本造紙 (Nippon Paper Industries, 3863.T) 九州熊本八代廠受 7 月底餘震影響，對特種紙、高級食品包裝卡紙產線進行預防性停工設備巡檢與校正。雖然公司啟動跨廠調度應變，但亞太地區部分高階食品塗佈紙短期交期延長 7–10 天，台灣與東南亞進口紙行正密切協調出貨船期。", "med", 0, "approved"),
        ("N2026W33_JP_08", "日本紙袋龍頭 The Pack (ザ・パック) 與 Super Bag 擴大外帶餐飲與零售全紙質牛皮紙袋出貨", "JP", "PAPER_BAG", '["紙袋","包裝","食品包裝","企業"]', "2026-08-10", "2026-08-18", "The Pack IR / Super Bag IR", "https://www.thepack.co.jp/", "日本第一大紙袋製造商 The Pack (ザ・パック, 3950.T) 與 Super Bag (スーパーバッグ, 3945.T) 發布最新經營月報。受惠於日本國內百貨商場、連鎖餐飲與烘焙外帶全面落實「脫塑紙化」，高強度牛皮購物紙袋與全紙質提把紙袋訂單強勁。兩大廠導入多層防潮強化工藝與全自動高速製袋機，單季紙袋出貨量創近三年同期新高。", "high", 0, "approved"),
        ("N2026W33_JP_09", "日本包裝商社 Shimojima (シモジマ) 擴建店舖牛皮紙袋與環保包裝資材專屬物流中心", "JP", "PACKAGING", '["包裝","紙袋","企業"]', "2026-08-09", "2026-08-18", "Shimojima IR", "https://www.shimojima.co.jp/", "日本包裝與店舖用品專業商社 Shimojima (シモジマ, 7482.T) 宣布於關東地區擴建自動化綠色包裝物流中心，加強零售門市與餐飲業者之牛皮紙袋、防油包裝紙及生物降解紙餐盒之即時配送能力，因應中小企業在禁塑規範下對少量多樣環保紙袋的迫切需求。", "med", 0, "approved"),
        ("N2026W33_JP_10", "TOPPAN (凸版印刷) 與 DNP (大日本印刷) 推出 Packaging 4.0 智慧溯源無塑紙容器", "JP", "PRINTING", '["印刷","包裝","食品包裝","企業"]', "2026-08-11", "2026-08-18", "TOPPAN Holdings / DNP IR", "https://www.holdings.toppan.com/", "日本印刷龍頭 TOPPAN (7911.T) 與大日本印刷 (DNP, 7912.T) 同步推出結合 NFC 晶片與 QR Code 數位產品護照 (DPP) 之新一代智慧無塑紙盒。此類產品符合歐盟 PPWR 溯源要求，兼具高氣體阻隔性與易拆解回收性，瞄準歐美跨國醫藥、高級食品與美妝品牌外銷市場。", "high", 0, "approved"),
        ("N2026W33_GL_01", "Suzano 巴西 Cerrado 255 萬噸桉木漿產線全能運轉，出口淨價 $562/噸確立低成本護城河", "GLOBAL", "RAW_MATERIAL", '["產量","原料","價格","企業"]', "2026-08-01", "2026-08-18", "Suzano S.A. 6-K / SEC EDGAR", "https://www.sec.gov/", "全球最大短纖漿生產商 Suzano 巴西 Cerrado 項目（年產能 255 萬噸漂白桉木漿）稼動率達到 100% 全能運轉。公司最新 6-K 財報申報顯示，其全球商品漿平均實現出口淨價為 USD 562/噸，配合每噸低於 USD 200 的極低現金生產成本，為全球短纖木漿市場奠定了極為堅實的價格底部支撐。", "high", 0, "approved"),
        ("N2026W33_GL_02", "智利 Arauco MAPA 專案新產能投放順利，8 月亞洲針葉漿牌價 USD 670/噸維持築底", "GLOBAL", "RAW_MATERIAL", '["原料","價格","產量","企業"]', "2026-08-07", "2026-08-18", "Arauco IR / Fastmarkets", "https://www.arauco.com/", "智利林漿紙巨頭 Arauco 發布產能品質最新報告，MAPA 專案 156 萬噸桉木漿新產線運行平穩。Arauco 8 月對華外盤牌價維持在：漂針漿 (NBSK) USD 670/噸、漂闊漿 (BHKP 明星) USD 590/噸、本色木漿 (UKP 金星) USD 640/噸，顯示南美漿廠挺價意願強烈，亞洲到岸價進入實質築底盤整期。", "med", 0, "approved"),
        ("N2026W33_GL_03", "芬蘭 UPM 烏拉圭 Paso de los Toros 210 萬噸桉木漿廠稼動率達 95%，支撐歐亞商品漿供應", "EU", "RAW_MATERIAL", '["產量","原料","企業"]', "2026-08-04", "2026-08-18", "UPM-Kymmene IR", "https://www.upm.com/", "芬蘭生質材料巨頭 UPM 宣布烏拉圭 Paso de los Toros 桉木漿廠（年產能 210 萬噸）稼動率維持於 95% 高檔運作，鐵路專線與蒙特維多深水港物流裝載順暢。UPM 藉由低成本南美自產木漿供應歐洲與亞洲特種紙及生活用紙客戶，強化全球原料抗波動韌性。", "med", 0, "approved"),
        ("N2026W33_GL_04", "巴西 Klabin Puma II 廠全速增產塗佈牛皮卡紙與 Kraftliner，外銷亞洲與中東創季度新高", "GLOBAL", "PAPER_MILL", '["產量","包裝","企業"]', "2026-08-05", "2026-08-18", "Klabin S.A. IR", "https://ri.klabin.com.br/", "巴西綜合造紙龍頭 Klabin Puma II 專案 MP28 機台（年產 46 萬噸塗佈牛皮卡紙）與 MP27 Kraftliner 產能全面放量，單季出口亞洲與中東地區總量創歷史新高。Klabin 憑藉南美優質松木與桉木自製漿優勢，積極填補歐美工紙因價格飆漲而外溢的亞太包裝原紙缺口。", "med", 0, "approved"),
        ("N2026W33_LOG_01", "上海出口集裝箱運價指數 (SCFI) 8/14 報 3,355.24 點連 3 週反彈，美線運力偏緊", "GLOBAL", "LOGISTICS", '["價格","包裝","產業"]', "2026-08-14", "2026-08-18", "上海航運交易所 (SSE SCFI)", "https://www.sse.net.cn/", "上海出口集裝箱運價指數 (SCFI) 截至 2026 年 8 月 14 日報 3,355.24 點，較上週上漲 79.10 點（漲幅 2.41%），呈現連續三週反彈走勢。美西線每 FEU 運價維持在 $6,200–6,500、美東線 $7,300–7,600 高位。紅海繞航與航商空班使艙位持續偏緊，推高廢紙進口與成品紙外銷海運成本。", "high", 0, "approved"),
        ("N2026W33_LOG_02", "波羅的海乾散貨指數 (BDI) 8/17 收於 2,878 點，散裝木片船與煤炭船運價高檔震盪", "GLOBAL", "LOGISTICS", '["價格","原料","產業"]', "2026-08-17", "2026-08-18", "波羅的海交易所 (Baltic Exchange)", "https://www.balticexchange.com/", "波羅的海乾散貨指數 (BDI) 截至 2026 年 8 月 17 日報 2,878 點，維持於近半年高檔區間震盪。好望角型與巴拿馬型散裝船租金堅挺，澳洲木片進口至日本與台灣之散裝航運成本維持在每公噸 $28–32 美元，對紙廠長纖木片進口成本形成支撐。", "med", 0, "approved"),
        ("N2026W33_ENG_01", "中東地緣局勢推升國際原油，Brent 報 $91.55 / 桶、WTI 報 $85.31 / 桶，化工膠乳成本墊高", "GLOBAL", "LOGISTICS", '["價格","產業","包裝"]', "2026-08-17", "2026-08-18", "ICE Brent / NYMEX WTI", "https://www.theice.com/", "受中東地緣衝突與供給中斷擔憂影響，布蘭特原油 (Brent Crude) 8 月中旬突破每桶 91.55 美元，紐約輕原油 (WTI) 報 85.31 美元。國際油價走強帶動船用重油與陸運燃油附加費上升，同時推升造紙塗佈用丁苯膠乳 (SB Latex)、水性無塑淋膜樹脂等石化原料之採購成本。", "high", 0, "approved"),
        ("N2026W33_ENG_02", "亞太動力煤期貨報 $130–135/噸，秦皇島平倉價穩健，台廠汽電共生每噸紙蒸氣成本鎖定 NT$720–780", "GLOBAL", "LOGISTICS", '["價格","產業","企業"]', "2026-08-15", "2026-08-18", "globalCOAL / 經濟部能源署", "https://www.globalcoal.com/", "澳洲 Newcastle 動力煤期貨價格報每公噸 130–135 美元區間震盪，中國秦皇島 5500 大卡平倉價穩健於 830–850 元人民幣/噸。台灣造紙廠進口燃煤到港成本平穩，配合廠區生質能 SRF 鍋爐混燒，造紙每噸蒸氣成本鎖定於 720–780 元新台幣，熱電自給率優勢凸顯。", "med", 0, "approved")
    ]

    for n in news_seed:
        cursor.execute("""
        INSERT INTO industry_news (article_id, title, region, category, tags, publish_date, obs_date, source, source_url, summary, impact_level, selected_for_report, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(article_id) DO UPDATE SET
            title=excluded.title,
            region=excluded.region,
            category=excluded.category,
            tags=excluded.tags,
            publish_date=excluded.publish_date,
            obs_date=excluded.obs_date,
            source=excluded.source,
            source_url=excluded.source_url,
            summary=excluded.summary,
            impact_level=excluded.impact_level,
            selected_for_report=excluded.selected_for_report,
            status=excluded.status,
            updated_at=datetime('now', 'localtime')
        """, n)

    conn.commit()
    conn.close()
    print("  ✓ SQLite 資料庫 paperluz.db 初始化與關聯表 Seed 完成 (Schema v11.2 JP Paper Mills & Paper Bag Expansion)")
    return 0


def cmd_import_csv(args=None):
    """將 price_series.csv 匯入至 paperluz.db"""
    if not os.path.exists(CSV_FILE):
        print(f"  ✗ 找不到 CSV 檔案：{CSV_FILE}")
        return 1

    cmd_init(args)
    conn = get_db_connection()
    cursor = conn.cursor()

    count = 0
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("series_id"):
                continue

            def parse_float(val):
                if val is None or val.strip() == "":
                    return None
                try:
                    return float(val)
                except ValueError:
                    return None

            cursor.execute("""
            INSERT INTO price_series (
                series_id, series_name, geo, product, price_type, currency, unit, freq,
                obs_date, period, value, value_low, value_high, delta, delta_unit,
                source, source_url, confidence, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(series_id, obs_date, price_type) DO UPDATE SET
                series_name=excluded.series_name,
                geo=excluded.geo,
                product=excluded.product,
                currency=excluded.currency,
                unit=excluded.unit,
                freq=excluded.freq,
                period=excluded.period,
                value=excluded.value,
                value_low=excluded.value_low,
                value_high=excluded.value_high,
                delta=excluded.delta,
                delta_unit=excluded.delta_unit,
                source=excluded.source,
                source_url=excluded.source_url,
                confidence=excluded.confidence,
                note=excluded.note,
                updated_at=datetime('now', 'localtime')
            """, (
                row["series_id"], row["series_name"], row["geo"], row["product"],
                row["price_type"], row["currency"], row["unit"], row["freq"],
                row["obs_date"], row["period"], parse_float(row.get("value")),
                parse_float(row.get("value_low")), parse_float(row.get("value_high")),
                parse_float(row.get("delta")), row.get("delta_unit") or "",
                row["source"], row.get("source_url") or "", row.get("confidence") or "med",
                row.get("note") or ""
            ))
            count += 1

    conn.commit()
    conn.close()
    print(f"  ✓ 成功匯入 {count} 筆觀測值至 paperluz.db")
    return 0


def cmd_export_csv(args=None):
    """將 paperluz.db 之 price_series 表同步導出至 price_series.csv"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT series_id, series_name, geo, product, price_type, currency, unit, freq,
               obs_date, period, value, value_low, value_high, delta, delta_unit,
               source, source_url, confidence, note
        FROM price_series
        ORDER BY obs_date ASC, series_id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    headers = [
        "series_id", "series_name", "geo", "product", "price_type", "currency",
        "unit", "freq", "obs_date", "period", "value", "value_low", "value_high",
        "delta", "delta_unit", "source", "source_url", "confidence", "note"
    ]

    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow([
                r["series_id"], r["series_name"], r["geo"], r["product"],
                r["price_type"], r["currency"], r["unit"], r["freq"],
                r["obs_date"], r["period"],
                "" if r["value"] is None else r["value"],
                "" if r["value_low"] is None else r["value_low"],
                "" if r["value_high"] is None else r["value_high"],
                "" if r["delta"] is None else r["delta"],
                r["delta_unit"] or "",
                r["source"], r["source_url"] or "", r["confidence"] or "",
                r["note"] or ""
            ])

    print(f"  ✓ 成功導出 {len(rows)} 筆資料至 price_series.csv")
    return 0


def cmd_validate(args=None):
    """資料庫完整性與來源稽核"""
    cmd_import_csv(args)
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n  ╔══════════════════════════════════════════════╗")
    print("  ║    Paperluz Local DB 完整性與 Pipeline 稽核   ║")
    print("  ╚══════════════════════════════════════════════╝\n")

    cursor.execute("SELECT COUNT(*) FROM source_registry")
    total_sources = cursor.fetchone()[0]
    print(f"  • 全球情報資訊源註冊總數 (source_registry): {total_sources} 個點位")

    cursor.execute("SELECT geo, COUNT(*) FROM source_registry GROUP BY geo")
    geo_dist = dict(cursor.fetchall())
    print(f"    - 地區分布: TW={geo_dist.get('TW',0)}, CN={geo_dist.get('CN',0)}, JP={geo_dist.get('JP',0)}, US={geo_dist.get('US',0)}, EU={geo_dist.get('EU',0)}, GLOBAL={geo_dist.get('GLOBAL',0)}")

    cursor.execute("SELECT COUNT(*) FROM price_series")
    total_obs = cursor.fetchone()[0]
    print(f"  • 大宗價格觀測值總數 (price_series): {total_obs} 筆")

    cursor.execute("SELECT COUNT(DISTINCT series_id) FROM price_series")
    total_series = cursor.fetchone()[0]
    print(f"  • 獨立價格序列數量 (series_id): {total_series} 條")

    cursor.execute("SELECT COUNT(*) FROM company_revenues")
    total_rev = cursor.fetchone()[0]
    print(f"  • 台灣紙廠月營收紀錄 (company_revenues): {total_rev} 筆")

    cursor.execute("SELECT COUNT(*) FROM industry_events")
    total_evt = cursor.fetchone()[0]
    print(f"  • 產業法規與事件紀錄 (industry_events): {total_evt} 筆")

    cursor.execute("SELECT COUNT(*) FROM industry_news")
    total_news = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM industry_news WHERE selected_for_report = 1")
    selected_news = cursor.fetchone()[0]

    print(f"  • 每週產業新聞候選庫總筆數 (industry_news): {total_news} 則 (包含日本與北美紙袋會社點位)")
    cursor.execute("SELECT COUNT(*) FROM price_forecasts")
    total_fcst = cursor.fetchone()[0]
    print(f"  • 全鏈價格預測模型指標 (price_forecasts): {total_fcst} 筆 (涵蓋能源、木漿、紙品 1M/3M/6M 區間推估)")

    # 檢查標籤覆蓋率
    cursor.execute("SELECT tags FROM industry_news")
    all_tags = []
    for r in cursor.fetchall():
        try:
            t_list = json.loads(r[0])
            all_tags.extend(t_list)
        except Exception:
            pass
    from collections import Counter
    tag_counts = Counter(all_tags)
    print(f"  • 新聞標籤全域分佈 (含紙袋 PAPER_BAG 與能源 ENERGY): {dict(tag_counts)}")

    cursor.execute("SELECT confidence, COUNT(*) FROM price_series GROUP BY confidence")
    conf_dist = dict(cursor.fetchall())
    print(f"  • 價格品質自信度分布: High={conf_dist.get('high',0)}, Med={conf_dist.get('med',0)}, Low={conf_dist.get('low',0)}")

    cursor.execute("SELECT COUNT(*) FROM price_series WHERE (source_url IS NULL OR source_url = '') AND confidence != 'none'")
    missing_url = cursor.fetchone()[0]
    if missing_url > 0:
        print(f"  ⚠️  警告: 有 {missing_url} 筆資料缺少原始來源 URL！")
    else:
        print("  ✓ 所有具體觀測值均具備完整來源 URL 追蹤")

    conn.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Paperluz Enterprise DB Manager CLI v12.0")
    subparsers = parser.add_subparsers(dest="command", help="子指令")

    subparsers.add_parser("init", help="初始化 SQLite 資料庫")
    subparsers.add_parser("import", help="從 CSV 匯入至 SQLite")
    subparsers.add_parser("export", help="從 SQLite 導出至 CSV")
    subparsers.add_parser("validate", help="稽核資料庫完整性")

    args = parser.parse_args()
    if args.command == "init":
        return cmd_init(args)
    elif args.command == "import":
        return cmd_import_csv(args)
    elif args.command == "export":
        return cmd_export_csv(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        cmd_import_csv(args)
        return cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())

