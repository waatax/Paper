# Paperluz · 全球與亞洲紙業情報每週自動聚合標準作業程序 (SOP)
> **Standard Operating Procedure: Weekly Pulp & Paper Intelligence Gathering & Aggregation Pipeline**  
> **版本**：v3.0（全面涵蓋美國 IP/Westrock、歐洲 UPM、智利 Arauco/CMPC、全球木片鏈、日本三大廠、中國/印尼 APP 與台灣造紙鏈）  
> **發行機構**：光網資訊 Luznet ∕ Paperluz 產業情報  

---

## 📌 一、 SOP 目的與適用範疇 (Purpose & Scope)

### 1.1 目的
規範 Paperluz 平台每週定期自動抓取、清洗、去重、分類、歸檔全球造紙、木漿與木片原料產業最新新聞與大宗報價，作為每週週報（MD / HTML / PDF）與即時快訊的權威情報來源。

### 1.2 監控對象與地域板塊劃分
1. **🇺🇸 北美造紙與包裝巨頭 (US Paper & Packaging)**：
   - **International Paper (IP · NYSE: IP)**：網絡優化（關閉老舊紙器廠）、9/1 工紙調價 +$80/短噸、收購 NORPAC 擴展西岸包裝原紙。
   - **Smurfit Westrock (SW · NYSE: SW)**：合併整合綜效（目標 2030 EBITDA 達 70 億美元）、關閉 8 座低效能紙器廠與 1 座造紙廠、9/1 箱板紙調價 +$100/短噸。
   - **Packaging Corporation of America (PCA · NYSE: PKG)**：9/1 領銜喊漲 +$140/短噸、瓦楞紙箱出貨量與毛利監控。
2. **🇪🇺 歐洲紙業與生化材料龍頭 (Europe Leaders)**：
   - **UPM-Kymmene (UPM · UPM.HE)**：烏拉圭 Paso de los Toros 210 萬噸 BHKP 巨型漿廠全產量運轉、德國 Leuna 生物精煉廠（木質素、生質乙二醇）、WISA 合板事業分拆上市、歐洲文化紙合資。
   - **Stora Enso (STEAV.HE)** & **Mondi (MNDI.L)**：牛皮箱板紙（Kraftliner）、生質石墨烯負極材料、無塑食品包裝。
3. **🇨🇱/🇧🇷 南美主要漿廠 (South America Pulp Giants)**：
   - **Arauco Chile (智利 Arauco · 塞爾洛薩阿勞科)**：MAPA 項目 156 萬噸尤加利闊葉漿新線與 Horcones 輻射松針葉漿線運轉、亞洲美金盤月度牌價（明星 BHKP / 銀星 NBSK / 金星 UKP）、林業生質能發電。
   - **Empresas CMPC (CMPC.SN)**：智利與巴西 Guaíba 漿廠、Nature Care 40 永續轉型。
   - **Suzano (SUZ)**：Cerrado 255 萬噸 BHKP 產能釋放、Q2 EBITDA 47 億雷亞爾、收購 Arbex 擴展生活用紙。
4. **🪵 全球木片與林業原料鏈 (Woodchips & Global Fiber)**：
   - **越南 (Vietnam)**：全球最大金合歡（Acacia）與尤加利木片出口國，主要出口至中國、日本與台灣。
   - **澳洲 (Australia)**：優質藍桉（Eucalyptus Globulus）木片，離岸價 AUD 250–267/BDMT。
   - **北美與歐洲 (North America & Nordics)**：南方黃松（SYP）、花旗松與北歐針葉木片，日本進口木片 CIF $198.4/噸基準。
5. **🇯🇵 日本市場三大巨頭 (Japan Big 3)**：
   - **王子控股 Oji Holdings (3861.T)**：中期計畫 2027（ROE 8% 目標）、越南同奈 1.04 億美元液體紙盒廠、AUROVISCO CNF 奈米纖維、無酚熱感紙。
   - **大王製紙 Daio Paper (3880.T)**：Transformation 2035、Elleair / GOO.N 個人護理調價修復毛利、海外重組、磐城廠低碳鍋爐。
   - **日本製紙 Nippon Paper (3863.T)**：中期計畫 2030（營益 600 億日圓）、SHIELDPLUS® 高阻隔包裝紙、cellenpia® CNF、液體紙盒充填系統。
6. **🇨🇳 中國 APP 金光集團 ∕ 博匯紙業 (China APP & Bohui)**：
   - 白卡紙（Ivory Board / FBB）市場價格與「減產挺價」博弈（3 月與 7 月各喊漲 200 元/噸）。
   - **博匯紙業 (600966.SH)** 財報、數智化全流程成本攻堅、零塑紙杯紙與東南亞/中東外銷。
7. **🇮🇩/🇸🇬 東南亞主要漿廠 (Southeast Asia Pulp & Fiber)**：
   - **APP 印尼 (Indah Kiat INKP.JK / OKI)**：西爪哇 Karawang 綠地包裝基地（日產 2,000 噸 OCC 回收漿新線）、Foopak 無塑淋膜紙盒、EUDR 全林區 GPS 溯源。
   - **APRIL (RGE 金鷹集團 / 廖內漿紙 Riau Andalan)**：蘇門答臘巨型 BHKP 產能與黏膠短纖垂直整合。
8. **🇹🇼 台灣造紙四大廠與紙容器加工群 (Taiwan Paper Big 4 & Food Packaging Converters)**：
   - 正隆 (1904)、榮成 (1909)、永豐餘 (1907)、華紙 (1905 益利疊/非塑食安卡紙)。
   - 台灣在地紙器與食品容器龍頭：捷比達 (GPPC)、富利康、永純、廣源、銘傳，以及連鎖餐飲/手搖飲/烘焙外帶紙袋紙杯採購標案。
9. **🥡 全球與區域食品包裝、紙袋與模塑纖維板塊 (Global Food Packaging & Molded Fiber)**：
   - **🇹🇼 台灣市場**：環境部 (MOENV) 一次性餐具減塑政策、外帶紙杯回收與自備優惠推動、水性無氟 (PFAS-free) 阻隔塗層替換進展。
   - **🇨🇳 中國市場**：外賣紙袋、白卡紙杯紙（APP/博匯/太陽）、甘蔗渣/竹漿紙模塑出海（眾鑫股份、韶能股份、裕同科技）、GB 4806.10 食品塗層新規。
   - **🇯🇵 日本市場**：超商（7-11/Lawson/FamilyMart）脫塑紙容器、王子食品包裝、日本製紙 SHIELDPLUS 高阻隔紙、The Pack (ザ・パック) 與 Shimojima 高級紙袋。
   - **🇺🇸 美國市場**：速食巨頭 (McDonald's/Starbucks) QSR 紙袋與模塑轉型、FDA 全氟化學物 (PFAS) 禁用、Graphic Packaging、Novolex、Huhtamaki。
   - **🇦🇺/🇳🇿 紐澳市場**：紐西蘭 Waste Minimisation 禁用難回收塑膠餐具、澳洲 APCO 2025/2026 包裝協議目標、Detmold Group、無氟植纖餐盒需求。
   - **🌏 東南亞市場**：SCG Packaging 綠色包裝併購擴產、印尼 APP Foopak BioContainer 出口、越南外銷包裝代工聚落。

---

## ⏰ 二、 每週標準作業節奏 (Weekly Operational Rhythm)

```
每週五 16:00 / 每週日 18:00
      │
      ▼
【步驟 1：自動執行聚合腳本】───► 輸出 news_snapshot_YYYY-MM-DD.{json, md}
      │
      ▼
【步驟 2：AI / 人工焦點篩選】───► 評定 3~5 則高質感核心焦點 (供需意涵 + 對台意涵)
      │
      ▼
【步驟 3：大宗價格時序登錄】───► 增補至 Reports/data/price_series.csv
      │
      ▼
【步驟 4：每週週報產製管線】───► python build_report.py new ──► 生成 MD / HTML / PDF
```

---

## 🛠️ 三、 命令列操作指引 (CLI Usage)

在專案根目錄下執行以下指令：

```bash
# 1. 執行即時新聞聚合並自動儲存當週快照 (JSON + MD)
python search_paper_news.py --save

# 2. 靜音模式（適用於背景排程定時任務）
python search_paper_news.py --save --quiet
```

### 產出檔案路徑：
- **JSON 結構化數據**：`Reports/data/news_snapshots/news_snapshot_YYYY-MM-DD.json`
- **Markdown 檢閱報告**：`Reports/data/news_snapshots/news_snapshot_YYYY-MM-DD.md`

---

## 🤖 四、 定時自動化排程建置方案 (Automation Setup)

### 方案 A：Windows 工作排程器 (Windows Task Scheduler)
適合本地 Windows 伺服器或工作站，設定每週五下午 16:30 自動執行：

```powershell
# 以系統管理員身分在 PowerShell 執行建立排程任務
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "search_paper_news.py --save --quiet" -WorkingDirectory "c:\Users\User\OneDrive\文件\Antigravity\Paperluz"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 4:30PM
Register-ScheduledTask -TaskName "Paperluz_Weekly_News_Fetcher" -Action $Action -Trigger $Trigger -Description "每週五定時抓取全球與亞洲紙業情報快照"
```

### 方案 B：GitHub Actions 定時工作流 (雲端自動化)
可在 `.github/workflows/weekly_news.yml` 中建立定時工作流：

```yaml
name: Weekly Paper News Aggregation

on:
  schedule:
    # 每週五 UTC 08:00 (台北時間 16:00) 自動觸發
    - cron: '0 8 * * 5'
  workflow_dispatch:

jobs:
  aggregate-news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run News Aggregation Engine
        run: |
          python search_paper_news.py --save --quiet
      - name: Commit & Push News Snapshots
        run: |
          git config --global user.name "Paperluz News Bot"
          git config --global user.email "bot@paperluz.internal"
          git add Reports/data/news_snapshots/
          git commit -m "chore: auto-update weekly paper news snapshot [skip ci]" || exit 0
          git push
```

---

## 🔍 五、 四層品質檢核規範 (4-Tier Quality Gate)

1. **去重與時效過濾**：自動依標題與 URL 清洗近 7–14 天重複新聞。
2. **來源分級原則**：
   - **甲級（權威）**：企業官方 IR（IP, Smurfit Westrock, UPM, Arauco, Suzano, Oji, Daio, NPI, APP）、各國證交所 (NYSE/TSE/TWSE/SSE/IDX/BCS)、Fastmarkets RISI。
   - **乙級（主流專業）**：Packaging Dive, 卓創資訊, 生意社, 日經, 日刊工業新聞, 工商時報。
   - **丙級（一般轉載）**：不得作為單一佐證，需交叉比對。
3. **數據一律美元優先 (USD-First)**：美金數值為主要標註，在地貨幣（CLP / BRL / EUR / JPY / RMB / TWD / IDR）以括號備註。
4. **禁止虛構與幻覺**：AI 僅負責梳理與傳導分析，涉及產量、價格、營收數字必須 100% 忠於原始新聞與財報。

---

## 📚 六、 下游週報出刊整合 (Downstream Newsletter Pipeline)

取得每週新聞快照後，進入 Paperluz 標準出刊流程：

```bash
# 1. 建立新一期報告骨架
python Reports/build_report.py new --issue {NNN} --date {YYYY-MM-DD} --theme "主軸焦點"

# 2. 編輯並校驗報告結構
python Reports/build_report.py validate PaperLuz-{NNN}_{YYYY-MM-DD}

# 3. 產出 A4 PDF 交付檔
python Reports/build_report.py pdf PaperLuz-{NNN}_{YYYY-MM-DD}

# 4. 執行 18 項品質檢核清單
python Reports/build_report.py checklist PaperLuz-{NNN}_{YYYY-MM-DD}
```

---
*© 2026 光網資訊 Luznet ∕ Paperluz 產業情報. All rights reserved.*
