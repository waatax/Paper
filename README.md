# Paperluz · 全球與台灣紙業產業情報平台
> **Global Pulp & Paper Industry Intelligence Hub & Automated Market Analytics**  
> 發行機構：光網資訊 Luznet ∕ Paperluz 產業情報  
> 官方即時入口網站：[https://waatax.github.io/Paper/](https://waatax.github.io/Paper/) ｜ [English Edition](https://waatax.github.io/Paper/EN/)

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Online%20Active-brightgreen.svg)](https://waatax.github.io/Paper/)
[![Weekly Issues](https://img.shields.io/badge/Weekly%20Reports-Issue%20001--006%20Published-blue.svg)](./Reports/)
[![Formats](https://img.shields.io/badge/Formats-HTML%20%7C%20Markdown%20%7C%20A4%20PDF-orange.svg)](./Reports/)
[![Bilingual](https://img.shields.io/badge/Language-繁體中文%20%7C%20English-purple.svg)](./EN/)
[![Zero-Gap PDF](https://img.shields.io/badge/PDF-A4%20Zero--Gap%20Print-success.svg)](./Reports/)

---

## 📌 平台核心定位 (Overview)

**Paperluz** 是專為造紙、包裝、紙商與印刷產業打造的現代化產業情報資料庫與自動化播報平台。涵蓋國際木漿、美廢、工紙調價、地緣能源油價、台廠營收財報與歐盟 PPWR / EUDR 法規全鏈分析。

### 🌟 核心特色 (Key Features)

1. **雙語官方門戶 (Bilingual GitHub Pages Portal)**：
   - 繁體中文版：[`index.html`](https://waatax.github.io/Paper/)
   - 英文國際版：[`EN/index.html`](https://waatax.github.io/Paper/EN/)
   - 支援深色模式 (Dark)、明亮模式 (Light) 與紙質閱讀模式 (Paper Texture)。
2. **即時大宗行情跑馬燈 (Live Market Ticker)**：
   - 國際長纖 (NBSK)、短纖 (BHKP)、美廢 (US OCC 11#)、上海期貨、布蘭特原油、SCFI 貨櫃運價、台廠營收等數據。
3. **週報檔案庫與內建閱讀器 (Issue Archives & Modal Reader)**：
   - 支援即時關鍵字搜尋與分類標籤過濾。
   - 內建 In-App Modal Reader，一鍵在線閱讀 HTML 完整報告、下載 A4 Zero-Gap 專業 PDF 或檢視 Markdown 原文。
4. **互動式價差趨勢動態雷達 (Interactive Data Radar)**：
   - 長短纖木漿價差 (NBSK - BHKP Spread) 結構性變動。
   - 工紙原物料利差 (Linerboard - OCC Spread) 與景氣榮枯臨界線。
   - 台灣上市紙廠（正隆、榮成、永豐餘、華紙）月營收與年增率 (YoY)。
5. **毛利敏感度動態試算器 (Sensitivity Simulator)**：
   - 即時模擬美廢進價、工紙售價與每噸蒸汽能耗成本對毛利率的影響。
6. **全球法規倒數雷達 (Regulatory Milestones)**：
   - 歐盟 PPWR 包裝法規、EUDR 森林砍伐規章、PFAS / PFHxA 無毒化禁令、台灣碳費徵收進程即時倒數。

---

## 📂 目錄結構 (Directory Layout)

```
Paperluz/
├── .github/
│   └── workflows/
│       └── deploy.yml                       ← GitHub Actions Pages 自動部署工作流
├── .nojekyll                                ← 確保 GitHub Pages 繞過 Jekyll 靜態建置
├── index.html                               ← 繁體中文官方門戶首頁 (GitHub Pages 進入點)
├── 404.html                                 ← 自訂 404 頁面 (支援雙語與暗色主題)
├── README.md                                ← 專案主說明文件
├── paperluz.md                              ← Paperluz 系統架構與業務規格書
├── convert_pdf.py                           ← 統一 Markdown / HTML 至 A4 PDF 轉檔引擎
├── search_paper_news.py                     ← 全球與亞洲紙業新聞每週自動聚合引擎 (支援 --save / --quiet)
├── EN/
│   └── index.html                           ← 英文官方門戶首頁 (English Edition)
└── Reports/
    ├── README.md                            ← 報告規範與標準範本規格
    ├── SOP_Weekly_News_Aggregation.md       ← 全球與亞洲紙業情報每週自動聚合標準作業程序 (SOP v2.0)
    ├── Paperluz_Newsletter_Template_Spec.md ← 視覺排版規格書 (v9.2)
    ├── build_report.py                      ← 週報產製管線主腳本
    ├── build_pdf.py                         ← Edge 無頭列印 PDF 產製器
    ├── templates/
    │   ├── report_template.html             ← 黃金 HTML 模板
    │   └── report_template.md               ← 黃金 MD 模板
    ├── data/
    │   ├── price_series.csv                 ← 大宗價格時序資料庫
    │   ├── company_monthly_revenue.csv      ← 台灣紙廠月營收資料庫
    │   └── paperluz.db                      ← SQLite 產業關聯資料庫
    ├── PaperLuz-001_2026-07-31.{html,md,pdf}
    ├── PaperLuz-001_2026-07-31_EN.{html,md,pdf}
    ├── PaperLuz-002_2026-08-07.{html,md,pdf}
    ├── PaperLuz-002_2026-08-07_EN.{html,md,pdf}
    ├── PaperLuz-003_2026-08-14.{html,md,pdf}
    ├── PaperLuz-003_2026-08-14_EN.{html,md,pdf}
    ├── PaperLuz-004_2026-08-21.{html,md,pdf}
    ├── PaperLuz-004_2026-08-21_EN.{html,md,pdf}
    ├── PaperLuz-005_2026-08-28.{html,md,pdf}
    ├── PaperLuz-005_2026-08-28_EN.{html,md,pdf}
    ├── PaperLuz-006_2026-09-04.{html,md,pdf}
    └── PaperLuz-006_2026-09-04_EN.{html,md,pdf}
```

---

## 🚀 出刊清單 (Published Issues)

| 期數 | 出刊日期 | 中文版 (HTML / PDF / MD) | 英文版 (HTML / PDF / MD) | 主題焦點 |
|:---:|:---:|:---:|:---:|:---|
| **006** | 2026-09-04 | [HTML](./Reports/PaperLuz-006_2026-09-04.html) · [PDF](./Reports/PaperLuz-006_2026-09-04.pdf) · [MD](./Reports/PaperLuz-006_2026-09-04.md) | [HTML](./Reports/PaperLuz-006_2026-09-04_EN.html) · [PDF](./Reports/PaperLuz-006_2026-09-04_EN.pdf) · [MD](./Reports/PaperLuz-006_2026-09-04_EN.md) | 北美工紙 9/1 調價全面生效落袋 × Suzano 領銜亞洲漿價調升 $20 × 中國 GB 4806.10 塗層新規施行 × 正隆 H1 獲利暴增 52 倍 |
| **005** | 2026-08-28 | [HTML](./Reports/PaperLuz-005_2026-08-28.html) · [PDF](./Reports/PaperLuz-005_2026-08-28.pdf) · [MD](./Reports/PaperLuz-005_2026-08-28.md) | [HTML](./Reports/PaperLuz-005_2026-08-28_EN.html) · [PDF](./Reports/PaperLuz-005_2026-08-28_EN.pdf) · [MD](./Reports/PaperLuz-005_2026-08-28_EN.md) | 北美工紙 9/1 調價倒數 3 天 × 原油破 $94 美元與海運 BSS 附加費 × 亞洲木漿備貨啟動 |
| **004** | 2026-08-21 | [HTML](./Reports/PaperLuz-004_2026-08-21.html) · [PDF](./Reports/PaperLuz-004_2026-08-21.pdf) · [MD](./Reports/PaperLuz-004_2026-08-21.md) | [HTML](./Reports/PaperLuz-004_2026-08-21_EN.html) · [PDF](./Reports/PaperLuz-004_2026-08-21_EN.pdf) · [MD](./Reports/PaperLuz-004_2026-08-21_EN.md) | 榮成分割轉型控股 × 北美工紙 9/1 調價倒數 × 歐盟 PPWR 正式生效與 PFAS 嚴格管制 |
| **003** | 2026-08-14 | [HTML](./Reports/PaperLuz-003_2026-08-14.html) · [PDF](./Reports/PaperLuz-003_2026-08-14.pdf) · [MD](./Reports/PaperLuz-003_2026-08-14.md) | [HTML](./Reports/PaperLuz-003_2026-08-14_EN.html) · [PDF](./Reports/PaperLuz-003_2026-08-14_EN.pdf) · [MD](./Reports/PaperLuz-003_2026-08-14_EN.md) | 船運費與能源連動評估 × 全鏈預測矩陣 × 歐盟 PPWR 強制生效 |
| **002** | 2026-08-07 | [HTML](./Reports/PaperLuz-002_2026-08-07.html) · [PDF](./Reports/PaperLuz-002_2026-08-07.pdf) · [MD](./Reports/PaperLuz-002_2026-08-07.md) | [HTML](./Reports/PaperLuz-002_2026-08-07_EN.html) · [PDF](./Reports/PaperLuz-002_2026-08-07_EN.pdf) · [MD](./Reports/PaperLuz-002_2026-08-07_EN.md) | 歐盟 PPWR 倒數五天 × PFAS 全面禁用 × 2026 紙包裝五大趨勢 |
| **001** | 2026-07-31 | [HTML](./Reports/PaperLuz-001_2026-07-31.html) · [PDF](./Reports/PaperLuz-001_2026-07-31.pdf) · [MD](./Reports/PaperLuz-001_2026-07-31.md) | [HTML](./Reports/PaperLuz-001_2026-07-31_EN.html) · [PDF](./Reports/PaperLuz-001_2026-07-31_EN.pdf) · [MD](./Reports/PaperLuz-001_2026-07-31_EN.md) | 北美箱板紙供給收縮 × 亞洲漿價底部盤整 × 歐盟包裝法規倒數 |

---

## 🛠️ 本地開發與預覽 (Local Preview)

您可以在本地使用任何靜態網頁伺服器（例如 Python 內建 HTTP Server）預覽網站：

```bash
# 在專案根目錄啟動伺服器
python -m http.server 8000

# 瀏覽器開啟：
# 中文版：http://localhost:8000
# 英文版：http://localhost:8000/EN/
```

### 產出 A4 PDF 交付檔

```bash
# 轉換全部報告至 A4 PDF
python convert_pdf.py --all

# 或轉換指定期數
python convert_pdf.py Reports/PaperLuz-004_2026-08-21.html
```

---

## 🌐 GitHub Pages 部署設定說明 (Deployment Setup)

本專案已完全相容於 GitHub Pages：
1. **GitHub Actions 模式 (推薦)**：已內建 [`.github/workflows/deploy.yml`](./.github/workflows/deploy.yml)，在 GitHub 倉庫設定 `Settings -> Pages -> Build and deployment -> Source` 選擇 **GitHub Actions** 即可自動部署。
2. **Branch 模式**：亦可直接選擇 `Deploy from a branch` 並指定 `master` (或 `main`) 分支的 `/ (root)` 目錄。

---

*© 2026 光網資訊 Luznet ∕ Paperluz 產業情報. All rights reserved.*
