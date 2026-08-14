# Paperluz Reports — 資料夾規範與標準範本規格

本資料夾存放 Paperluz 產業情報報告與其底層資料庫。上層 `paperluz.md` 為系統規格書，本資料夾為其產出。

---

## 一、出刊規則

| 項目 | 規格 |
|---|---|
| **出刊頻率** | 每週五 |
| **第一期** | 第 001 期（2026-07-31） |
| **最後一期** | 第 075 期（2027-12-31） |
| **總期數** | 75 期 |
| **涵蓋範圍** | 每期涵蓋出刊日前 7 天（週六至週五） |

---

## 二、目錄結構

```
Reports/
├── README.md                              ← 本檔
├── Paperluz_Newsletter_Template_Spec.md   ← 電子報與週報標準視覺格式規範（v9.2 範本檔）
├── PaperLuz-001_2026-07-31.md             ← 第 001 期（純文字版）
├── PaperLuz-001_2026-07-31.html           ← 第 001 期（高階視覺版）
├── PaperLuz-001_2026-07-31.pdf            ← 第 001 期（A4 PDF 對外交付版）
├── PaperLuz-002_2026-08-07.md             ← 第 002 期
├── PaperLuz-002_2026-08-07.html
├── PaperLuz-002_2026-08-07.pdf
├── build_report.py                        ← 產製管線主腳本
├── build_pdf.py                           ← PDF 產製器（Edge 無頭列印）
├── templates/
│   ├── report_template.html               ← 黃金 HTML 模板
│   ├── report_template.md                 ← 黃金 MD 模板
│   └── golden_css_hash.txt                ← CSS 指紋
└── data/
    ├── price_series.csv                   ← 大宗物資價格資料庫
    ├── price_series_schema.md             ← 資料庫結構定義
    ├── company_monthly_revenue.csv        ← 台灣上市紙廠月營收
    └── source_registry.md                 ← 來源清單與內部分級
```

---

## 三、命名規則

```
PaperLuz-{NNN}_{YYYY-MM-DD}.{ext}
```

- `{NNN}` — 三位數期數（001-075）
- `{YYYY-MM-DD}` — 出刊日（必為週五）
- `{ext}` — `.md` / `.html` / `.pdf`

範例：`PaperLuz-003_2026-08-14.html`

---

## 四、三檔並存原則

| 檔案 | 用途 | 規範要求 |
|---|---|---|
| `.md` | 版控、逐期 diff、餵給下游 AI | 包含完整文本與 6 大 KPI 卡片內容摘要 |
| `.html` | 螢幕閱讀、互動 SVG 圖表、轉 PDF 來源 | 採 3x2 KPI Grid、5 大向量 SVG 圖表、現代配色系統 |
| `.pdf` | 對外正式交付、客戶列印與訂閱發送 | **由 Edge 無頭列印產出，採 A4 緊湊無空白頁面優化** |

---

## 五、品質與格式規範（v9.2 專家標準）

1. **頁尾嚴格禁止下期預告**：頁尾只留產出時間、系統版本與發行機構。
2. **第一頁 3x2 網格卡片**：必須包含 6 大關鍵指標卡片（3 列 × 2 行對稱網格）。
3. **A4 PDF 零空白頁面優化**：嚴禁使用硬換頁指令。
4. **詳細格式模板與 CSS 規範**：請參閱 [`Paperluz_Newsletter_Template_Spec.md`](file:///c:/Users/User/OneDrive/文件/Antigravity/Paperluz/Reports/Paperluz_Newsletter_Template_Spec.md)。

---

## 六、自動化產製管線

```bash
# 首次初始化（僅需一次）
python build_report.py init

# 建立新期骨架（範例：第 003 期）
python build_report.py new --issue 003 --date 2026-08-14 --start 2026-08-08 --end 2026-08-14 --week 33 --theme "主軸描述"

# 編輯 HTML 與 MD 內容後...
python build_report.py validate PaperLuz-003_2026-08-14   # 9 項結構驗證
python build_report.py pdf PaperLuz-003_2026-08-14        # 產出 A4 PDF
python build_report.py checklist PaperLuz-003_2026-08-14  # 18 項完整品質檢核
python build_report.py status                              # 所有期數三檔狀態
```

---

## 七、期數索引

| 期數 | 出刊日 | 情報週期 | 主軸 | 狀態 |
|---|---|---|---|---|
| **001** | 2026-07-31 | W31（2026-07-25 ~ 07-31） | 北美箱板紙供給收縮 × 亞洲漿價底部盤整 × 歐盟包裝法規倒數 | ✅ 已發布 (MD+HTML+PDF) |
| **002** | 2026-08-07 | W32（2026-08-01 ~ 08-07） | 歐盟 PPWR 倒數五天 × PFAS 全面禁用 × 2026 紙包裝五大趨勢 | ✅ 已發布 (MD+HTML+PDF) |
| **003** | 2026-08-14 | W33（2026-08-08 ~ 08-14） | 船運費與能源連動評估 × 全鏈預測矩陣 × 歐盟 PPWR 強制生效 | ✅ 已發布 (MD+HTML+PDF) |
| 004 | 2026-08-21 | W34（2026-08-15 ~ 08-21） | 待產出 | 規劃中 |
| ... | 每週五 | — | — | — |
| 075 | 2027-12-31 | W52（2027-12-25 ~ 12-31） | 待產出 | 規劃中 |

---

## 八、GitHub Pages 官方門戶整合

根目錄 [`index.html`](file:///c:/Users/User/OneDrive/文件/Antigravity/Paperluz/index.html) 為 Paperluz 官方 GitHub Pages 入口網站，具備：
1. **即時大宗行情跑馬燈**（NBSK, BHKP, OCC, SCFI, Brent, 正隆/榮成營收）
2. **週報檔案庫與線上閱讀器**（支援即時關鍵字過濾、HTML 全螢幕閱讀、A4 PDF 下載與 MD 原文）
3. **互動式價差趨勢動態雷達**（長短纖木漿價差、工紙利差、台廠營收折線圖）
4. **全鏈預測矩陣與毛利敏感度試算器**（IEA/期貨計量模型、動態滑桿模擬單噸毛利與利差）
5. **全球法規即時倒數雷達**（歐盟 PPWR、EUDR、BPA 禁令、台灣碳費）

