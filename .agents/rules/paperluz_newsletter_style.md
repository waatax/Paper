# Paperluz 產業情報週報視覺排版規範與鐵律 (Workspace Rule v12.0)

> **適用範疇**：所有 Paperluz 電子報、週報、特刊 HTML / MD / PDF 產製與維護任務。

---

## 核心鐵律與排版規範

1. **頁尾資訊完全置中 (Footer Centering Standard)**
   - `footer` 元素必須設定 `text-align: center;`（包含螢幕顯示與 `@media print` 區域）。
   - 頁尾格式強制固定為：
     `<footer><b>產出時間</b>：YYYY-MM-DD　·　<b>系統版本</b>：Paperluz Engine v12.0 　·　<b>發行機構</b>：光網資訊 Luznet ∕ Paperluz 產業情報</footer>`
   - **嚴禁出現「下期預告」等預測性文字**。

2. **黃金 CSS 樣式指紋鎖定 (CSS Fingerprint)**
   - 所有報告 HTML 的 `<style>` 區塊必須與 `templates/report_template.html` 保持 100% 一致。
   - 當前黃金 CSS SHA-256 指紋記錄於 `templates/golden_css_hash.txt`。
   - 每次產出前必須通過 `python build_report.py validate <slug>` 與 `python build_report.py checklist <slug>`。

3. **三檔並存 100% 內容對應 (Three-File Parity)**
   - 每期報告必須同步更新並產生：`.html`、`.md`、`.pdf`。
   - PDF 必須由 `build_pdf.py`（Edge Headless 引擎）由 HTML 渲染產出，確保 A4 頁面無硬性截斷與零無意義空白（No-Blank-Gap）。

4. **視覺組件黃金規格**
   - **第一頁 3×2 KPI 網格**：`grid-template-columns: repeat(3, 1fr);`，固定 6 大卡片，具備陰影與微動效。
   - **目次導覽 (TOC)**：雙欄佈局 (`columns: 2; column-gap: 36px;`)，搭配帶背景色之章節序號。
   - **數據表格 (Tables)**：數字欄位齊右對齊 (`td.num`)，啟用 `font-variant-numeric: tabular-nums`；列印時設定 `break-inside: avoid;`。
   - **SVG 向量圖表 (5 大圖表)**：5 大 SVG 圖表必須標註雙幣別 (RMB / USD)，座標文字與數據點清晰對齊，避開截斷。

5. **能源與海運物流雷達標準 (Energy & Freight Logistics)**
   - 報告必須納入國際原油 (Brent / WTI)、台灣/中國/日本三地煤炭價格 (Newcastle Coal, 秦皇島動力煤, 台灣/日本進口燃煤 CIF) 與海運貨櫃/散裝運價 (SCFI / BDI)。

6. **圖表後全鏈預測矩陣專屬 SECTION (Predictive Radar)**
   - 緊接於「三、價格波動與趨勢圖表」5 大 SVG 圖表之後，必須建立 **3.6「全鏈預測矩陣與情境推估 (Forward Predictive Radar)」**。
   - 包含：能源、漿價、紙價未來 1M / 3M / 6M 目標區間與機率、多情境分析 (Base 60% / Bull 25% / Bear 15%)、造紙毛利敏感度矩陣與避險採購策略。

7. **全平台貨幣標註鐵律 (USD-First Primary Currency Standard)**
   - **主要貨幣一律使用美金 (USD / $)**：所有即時市場行情、週報章節、數據表格、KPI 卡片、SVG 向量圖表與 PDF 交付文件，核心數值均優先以美金計價。
   - **附註在地貨幣 (RMB / TWD / EUR)**：美金數值後必須於括號或副標題附註對應幣別（如 `USD 680 / 噸 (RMB 4,820 / 噸)`、`USD 134–136 / 美噸 (約 RMB 950–965 / 噸)`、`USD 130.5 / 噸 (NT$ 4,200 / 噸)`）。
