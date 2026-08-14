# Paperluz 大宗物資價格與匯率 Local 資料庫 — 雙軌架構與 7 次檢討規範 (v10.0)

**系統檔案**：`paperluz.db` (SQLite 本地資料庫) ＋ `price_series.csv` (長格式版控備份檔)  
**管理腳本**：`manage_db.py`  
**版本**：v10.0（2026-08-11 專家團隊 7 次檢討定稿）  
**目標**：為台灣及全球紙業、紙包裝與紙漿產業提供實時、可追溯、具高比對度的數據基底。

---

## 一、Local 資料庫架構 7 次規劃檢討演進歷程 (DB 7 Iterations)

為了打造極致穩定且滿足高階決策的 Local 資料庫，專家團隊經歷 7 次遞進檢討：

1. **Iteration 1（架構選型評估）**：
   - **檢討**：單一平坦 CSV 雖易於 Git 版控，但缺乏 SQL 複合查詢能力與欄位關聯約束；而傳統 SQL 資料庫若無 CSV 匯出，則失去純文字檔動態 diff 與 AI 直接讀取能力。
   - **決策**：採用 **SQLite 本地資料庫 (`paperluz.db`) ＋ CSV 長格式 (`price_series.csv`) 雙向無損同步機制**。

2. **Iteration 2（五大主表 Schema 設計）**：
   - **檢討**：單一表無法滿足每日匯率、上市紙廠財務營收與法規/產能倒數等不同維度數據。
   - **決策**：拆分為 5 大核心表：
     - `price_series`（大宗價格與港口/漿廠庫存）
     - `fx_rates`（外匯匯率：USDTWD, USDBRL, USDCNY, EURUSD）
     - `company_revenues`（台灣上市紙廠營收與自結損益）
     - `industry_events`（產能歲修停機與政策法規倒數）
     - `data_sources`（來源權威度分級與出處網址 registry）

3. **Iteration 3（口徑與單位中立化）**：
   - **檢討**：紙漿市場存在「漿廠公布牌價 (producer_list)」、「實際成交淨價 (realized_net)」、「亞洲美金盤現貨 (import_quote)」、「期貨結算價 (futures_settle)」四大口徑，若混淆將導致結論嚴重偏差。美噸 (short_ton, 907kg) 與公噸 (tonne, 1000kg) 亦有 10.2% 換算落差。
   - **決策**：在 `price_series` 強制標註 `price_type` 與 `unit`，禁止非同口徑直接相減。

4. **Iteration 4（數據品質與自信度分級）**：
   - **檢討**：網路情報來源品質參差不齊，未經驗證的預測不能與官方交易所數據混為一談。
   - **決策**：引入 4 級 `confidence` 評級 (`high` 交易所/財報/央行；`med` 卓創/Fastmarkets/新聞轉述；`low` 第三方推估；`none` 缺口)。無公開權威來源之序列（如台灣廢紙到廠價 `TW_OCC_MILL_TWD`）啟動人工詢價與海關進出口交叉驗證。

5. **Iteration 5（自動化指標與 Raw Material Spread 運算）**：
   - **檢討**：人工手算價差（如長短纖價差 SPREAD_BSKP_BHKP、美廢工紙利差 SPREAD_LINER_OCC）容易出錯且耗時。
   - **決策**：在 DB 寫入與查詢層實作動態 View 與 Python 計算器，自動生成價差與 YoY/MoM/WoW 變動率。

6. **Iteration 6（持久化與雙向同步機制）**：
   - **檢討**：手動同步 SQLite 與 CSV 容易造成雙軌數據不一致。
   - **決策**：開發 `manage_db.py import` 與 `manage_db.py export`，支援 UPSERT (ON CONFLICT) 邏輯，確保 CSV 寫入時自動觸發 SQLite 更新，SQLite 變更時自動導出標準 CSV。

7. **Iteration 7（DB 完整性稽核與 CLI 工具集）**：
   - **檢討**：缺乏自動化門禁容易導致缺失來源網址或日期格式不一致問題。
   - **決策**：建立 `manage_db.py validate` 指令，每次發布前強制執行 100% 來源網址稽核與自信度統計。

---

## 二、SQLite 表結構定義 (`paperluz.db`)

### 1. `price_series` (大宗物資價格與庫存主表)

```sql
CREATE TABLE price_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT NOT NULL,         -- 序列唯一碼 (如 SHFE_SP_SETTLE, CN_NBSK_SPOT_CNY)
    series_name TEXT NOT NULL,       -- 中文顯示名稱
    geo TEXT NOT NULL,               -- ISO-2 區域碼 (TW, CN, US, EU, BR, CL, JP)
    product TEXT NOT NULL,           -- 商品碼 (NBSK, BHKP, OCC, CONTAINERBOARD, FX 等)
    price_type TEXT NOT NULL,        -- 口徑碼 (spot, futures_settle, producer_list, realized_net, announced, cum_change)
    currency TEXT NOT NULL,          -- 幣別 (USD, CNY, TWD, EUR, PCT)
    unit TEXT NOT NULL,              -- 單位 (tonne, short_ton, 萬噸, pct)
    freq TEXT NOT NULL,              -- 頻率 (D 日, W 週, M 月, Q 季, E 事件)
    obs_date TEXT NOT NULL,          -- 觀測日期 (YYYY-MM-DD)
    period TEXT NOT NULL,            -- 期別描述 (如 2026-W33, 2026-08)
    value REAL,                      -- 主數值 (區間報價時為中值)
    value_low REAL,                  -- 區間低價
    value_high REAL,                 -- 區間高價
    delta REAL,                      -- 變動量
    delta_unit TEXT,                 -- 變動單位 (cny_wow, usd_mom, pct_yoy 等)
    source TEXT NOT NULL,            -- 數據來源機構
    source_url TEXT,                 -- 原始網址
    confidence TEXT CHECK(confidence IN ('high', 'med', 'low', 'none')),
    note TEXT,                       -- 備註與警語
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(series_id, obs_date, price_type)
);
```

### 2. `fx_rates` (每日外匯匯率表)

```sql
CREATE TABLE fx_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,              -- 幣別對 (USDTWD, USDBRL, USDCNY, EURUSD)
    base_ccy TEXT NOT NULL,
    quote_ccy TEXT NOT NULL,
    rate REAL NOT NULL,              -- 匯率數值
    obs_date TEXT NOT NULL,          -- 觀測日
    change_amount REAL,
    change_pct REAL,
    source TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(pair, obs_date)
);
```

### 3. `company_revenues` (台灣上市紙廠營收與獲利表)

```sql
CREATE TABLE company_revenues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,        -- 1904(正隆), 1905(華紙), 1907(永豐餘), 1909(榮成)
    company_name TEXT NOT NULL,
    year_month TEXT NOT NULL,        -- 營收月份 (YYYY-MM)
    revenue_ntd_hundred_m REAL,      -- 單月營收 (億元)
    mom_pct REAL,                    -- 月增率 (%)
    yoy_pct REAL,                    -- 年增率 (%)
    cum_revenue_hundred_m REAL,      -- 累計營收 (億元)
    pretax_profit_hundred_m REAL,    -- 自結稅前淨利 (億元)
    note TEXT,
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(stock_code, year_month)
);
```

---

## 三、CLI 管理工具 (`manage_db.py`) 指令說明

```bash
# 1. 初始化資料庫與建表
python Reports/data/manage_db.py init

# 2. 從 CSV 匯入至 SQLite (自動 UPSERT)
python Reports/data/manage_db.py import

# 3. 從 SQLite 導出最新數據至 CSV
python Reports/data/manage_db.py export

# 4. 執行完整性稽核與來源追蹤驗證
python Reports/data/manage_db.py validate
```

---

## 四、鐵律與寫入規範 (Non-negotiable Rules)

1. **AI 零生成原則**：所有數值、匯率、營收與變動率必須由採集腳本寫入 DB，AI 撰寫報告時僅能引用 DB 查詢結果，嚴禁生成或猜測任何數字。
2. **來源追蹤鐵律**：每一筆具體觀測值（Confidence != 'none'）必須包含可造訪之 `source_url`。
3. **口徑嚴格分軌**：漿廠牌價與期貨收盤價不得直接對比，長短纖價差與 Raw Material Spread 計算必須透過標準計算邏輯執行。
