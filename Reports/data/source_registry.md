# Paperluz 來源清單與全域揭露點位註冊表 (Source Registry v11.0)

**內部文件 — 不併入對外報告。** 報告正文只出現來源機構名稱與連結，分級與點位細節留在此處。

---

## 一、分級與確定性原則

| 級 | 定義 | 單獨採用 | 範例點位 |
|---|---|---|---|
| **甲** | 交易所、監管申報、政府統計、公司自身財報與重大訊息 | 可 | SEC EDGAR, MOPS, SHFE, EUR-Lex, 央行, 公司 IR |
| **乙** | 產業定價機構、公會統計、公司 IR 簡報、主流財經媒體轉述之機構數據 | 可，須標來源 | Fastmarkets RISI, Packaging Dive, 卓創資訊, 生意社, 日本製紙連合會 |
| **丙** | 產業媒體、商情網站、彙整型部落格 | **不可**，須有甲或乙級佐證 | pricey.jp, 一般財經新聞轉載論壇 |

---

## 二、多維度新聞標籤體系 (Tagging Architecture)

為確保每週與每日報導無需「大海撈針」，資訊管道自動針對所有入庫情報給予一至多個專屬標籤：

| 標籤名稱 | 代碼 / 鍵字 | 適用範圍 |
|---|---|---|
| **法規** | `REGULATION` | EUDR, PPWR, PFAS 限制, BPA 禁令, GB 4806.10, GB 31825 能耗限額, 資源循環推動法, 碳費 |
| **產業** | `INDUSTRY_TREND` | 產銷速報, 工紙反內卷, 生質能轉型, 綠色供應鏈, 出版紙張消長 |
| **價格** | `PRICE_MARKET` | SHFE 期貨結算價, 木漿現貨價, 美廢 OCC FAS, 紙廠提價函, Raw Material Spread |
| **產量** | `CAPACITY_PRODUCTION` | 巨型漿廠放量, 紙廠停機歲修, 永久關廠, 產能利用率(稼動率), 產能日曆 |
| **印刷** | `PRINTING` | 商業印刷, 圖書出版, 印刷油墨合規, 淋膜塗佈, 印刷機械進口 |
| **包裝** | `PACKAGING` | 瓦楞紙箱, 工業用紙, 彩盒, 折疊紙盒, Packaging Dive 追蹤 |
| **食品包裝**| `FOOD_PACKAGING` | 食品卡紙, 紙杯淋膜, 無塑防油塗層, BPA 雙酚A禁用, 衛生標準 |
| **原料** | `RAW_MATERIAL` | 漂針漿 (NBSK), 漂闊漿 (BHKP), 回收纖維 (OCC), 木片, 漿廠到岸價 |
| **紙袋** | `PAPER_BAG` | 牛皮紙袋 (Kraft Paper Bag), 手提袋, 外帶紙袋, 禁塑紙袋需求, ザ・パック, スーパーバッグ, シモジマ, Novolex |
| **企業** | `CORPORATE` | 台灣四大紙廠月營收, 日本造紙會社, 美股/港股/A股紙企財報, 併購 |

---

## 三、全域資訊源註冊總表 (Global Disclosure Matrix)

已完全同步寫入 SQLite `paperluz.db` 之 `source_registry` 主檔：

### 1. 日本造紙、包裝、印刷與紙袋會社 (Japan, JP)

| 來源 ID | 機構名稱 | 分級 | 存取方式 | 主要揭露內容 | 網址 / 點位 |
|---|---|---|---|---|---|
| `SRC_JP_JPA` | 日本製紙連合會 | 甲 | HTML_SCRAPE | 紙與紙板月度產銷速報、進出口統計、CO2 減排 | https://www.jpa.gr.jp/stats/ |
| `SRC_JP_OJI` | 王子控股 / 王子製紙 (3861.T) | 甲 | HTML_SCRAPE | 財報、價格修訂公告、海外紙漿與紙箱擴產 | https://www.ojiholdings.co.jp/en/ir/ |
| `SRC_JP_NIPPON` | 日本製紙 (NPI 3863.T) | 甲 | HTML_SCRAPE | 特種紙、包裝紙停機維修、紙容器回收 | https://www.nipponpapergroup.com/english/ir/ |
| `SRC_JP_DAIO` | 大王製紙 IR (3880.T) | 甲 | HTML_SCRAPE | 家庭用紙、工紙牌價調整、衛生紙進口動態 | https://www.daio-paper.co.jp/en/ir/ |
| `SRC_JP_HOKUETSU` | 北越 Corporation (3865.T) | 甲 | HTML_SCRAPE | 高階白紙板、印刷用紙、新潟紙漿廠運態 | https://www.hokuetsucorp.com/en/ir/ |
| `SRC_JP_MITSUBISHI` | 三菱製紙 (3864.T) | 甲 | HTML_SCRAPE | 特種印刷紙、熱敏紙、感光紙板價格 | https://www.mpm.co.jp/company/ir/ |
| `SRC_JP_THEPACK` | ザ・パック (The Pack 3950.T) | 甲 | HTML_SCRAPE | 日本第一大紙袋廠、手提購物紙袋、牛皮紙袋 | https://www.thepack.co.jp/ir/ |
| `SRC_JP_SUPERBAG` | スーパーバッグ (Super Bag 3945.T) | 甲 | HTML_SCRAPE | 零售與餐飲外帶紙袋、牛皮紙袋專利與產能 | https://www.superbag.co.jp/ir/ |
| `SRC_JP_SHIMOJIMA` | シモジマ (Shimojima 7482.T) | 甲 | HTML_SCRAPE | 包裝資材商社、店舖紙袋、防油紙餐袋、包裝紙 | https://www.shimojima.co.jp/ir/ |
| `SRC_JP_RENGO` | 連合製紙 / Tri-Wall (3941.T) | 甲 | HTML_SCRAPE | 瓦楞紙箱、重包裝紙箱、自動化設備 | https://www.rengo.co.jp/english/ir/ |
| `SRC_JP_TOPPAN` | TOPPAN Holdings (凸版印刷 7911.T) | 甲 | HTML_SCRAPE | 高階包裝印刷、無塑淋膜、數位包裝 | https://www.holdings.toppan.com/ja/ir/ |
| `SRC_JP_DNP` | 大日本印刷 (DNP 7912.T) | 甲 | HTML_SCRAPE | 包裝材料、環境對應型紙容器、商業印刷 | https://www.dnp.co.jp/ir/ |
| `SRC_JP_CAA` | 日本消費者廳 (CAA) | 甲 | HTML_SCRAPE | 食品接觸材質正面表列與紙類界線法規 | https://www.caa.go.jp/policies/policy/standards_evaluation/appliance/positive_list_new |

### 2. 中國大陸 (China, CN)

| 來源 ID | 機構名稱 | 分級 | 存取方式 | 主要揭露內容 | 網址 / 點位 |
|---|---|---|---|---|---|
| `SRC_CN_SHFE_SP` | 上海期貨交易所 (SHFE SP) | 甲 | API | 漂針漿期貨日結算價、收盤價、持倉量、倉單 | https://www.shfe.com.cn/ |
| `SRC_CN_SCI99` | 卓創資訊 (Sci99) | 乙 | HTML_SCRAPE | 國產廢紙、進口木漿現貨價、港口庫存、提價函 | https://www.sci99.com/pulp/ |
| `SRC_CN_100PPI` | 生意社 (100ppi) | 乙 | HTML_SCRAPE | 針葉漿/闊葉漿基準價、廢紙收購價、基差 | https://www.100ppi.com/vane/detail-1053.html |
| `SRC_CN_CPA` | 中國造紙協會 | 甲 | HTML_SCRAPE | 全國紙及紙板產量、進出口統計、產業政策 | http://www.chinappi.org/ |
| `SRC_CN_NDPAPER` | 玖龍紙業 IR (2689.HK) | 甲 | HTML_SCRAPE | 中期/年度業績、白卡紙/箱板紙漲價函 | https://www.ndpaper.com/tc/investor/announcements.php |
| `SRC_CN_LEEMAN` | 理文造紙 IR (2314.HK) | 甲 | HTML_SCRAPE | 包裝紙、衛生紙產能、海外造紙基地 | http://www.leemanpaper.com/investor.html |
| `SRC_CN_SUNPAPER` | 太陽紙業 IR (002078.SZ) | 甲 | HTML_SCRAPE | 文化紙、老撾林漿紙一體化產能、月度經營 | http://www.sunpapergroup.com/investor.html |
| `SRC_CN_SHANYING` | 山鷹國際 IR (600567.SH) | 甲 | HTML_SCRAPE | 再生廢紙回收、瓦楞紙箱報價 | http://www.shanyingintl.com/investor.html |
| `SRC_CN_BOHUI` | 博匯紙業 IR (600966.SH) | 甲 | HTML_SCRAPE | APP旗下白卡紙、食品卡紙調價公告 | http://www.bohui-paper.com/ |
| `SRC_CN_CHENMING` | 晨鳴紙業 IR (000488.SZ) | 甲 | HTML_SCRAPE | 銅版紙、白卡紙、自製木漿產量與財報 | http://www.chenmingpaper.com/ |
| `SRC_CN_SAMR_GB` | 國家市場監督管理總局 | 甲 | HTML_SCRAPE | GB 4806.10-2025食品接觸塗料、GB 31825能耗限額 | https://openstd.samr.gov.cn/ |

### 3. 台灣 (Taiwan, TW)

| 來源 ID | 機構名稱 | 分級 | 存取方式 | 主要揭露內容 | 網址 / 點位 |
|---|---|---|---|---|---|
| `SRC_TW_MOPS` | 公開資訊觀測站 (MOPS) | 甲 | MOPS_API | 台灣四大紙廠(1904,1905,1907,1909)月營收、重訊 | https://mops.twse.com.tw/ |
| `SRC_TW_1904` | 正隆 (1904.TW) IR | 甲 | HTML_SCRAPE | 平陽三期投產、紙箱報價、永續報告 | https://www.clc.com.tw/investor/ |
| `SRC_TW_1905` | 中華紙漿 (1905.TW) IR | 甲 | HTML_SCRAPE | 漿價傳導、益思無塑防油卡紙、綠能汽電共生 | https://www.chp.com.tw/news/detail/402 |
| `SRC_TW_1907` | 永豐餘 (1907.TW) IR | 甲 | HTML_SCRAPE | 家紙五月花、碳管理佈局、越南包裝廠 | https://www.yfy.com/zh-hant/investors/ |
| `SRC_TW_1909` | 榮成紙業 (1909.TW) IR | 甲 | HTML_SCRAPE | 自結稅前盈餘、中國廠區產能稼動率 | https://www.longchenpaper.com/investor/ |
| `SRC_TW_CBC` | 中央銀行外匯統計 | 甲 | HTML_SCRAPE | USD/TWD 新台幣銀行間收盤匯率 | https://www.cbc.gov.tw/tw/lp-645-1.html |
| `SRC_TW_MOENV` | 環境部氣候變遷署/循環署 | 甲 | HTML_SCRAPE | 《資源循環推動法》、碳費自主減量費率與開徵 | https://www.moenv.gov.tw/ |

### 4. 美國 / 北美 (US / North America)

| 來源 ID | 機構名稱 | 分級 | 存取方式 | 主要揭露內容 | 網址 / 點位 |
|---|---|---|---|---|---|
| `SRC_US_SEC_EDGAR` | 美國 SEC EDGAR 申報 | 甲 | SEC_EDGAR | IP, SW, PCA, Suzano 8-K / 10-Q 季報與調價申報 | https://www.sec.gov/edgar/searchedgar/companysearch |
| `SRC_US_FASTMARKETS` | Fastmarkets RISI | 乙 | HTML_SCRAPE | US OCC 美廢出口 FAS 價、NBSK/BHK 牌價 | https://www.fastmarkets.com/insights/ |
| `SRC_US_PACKAGINGDIVE` | Packaging Dive | 乙 | HTML_SCRAPE | 北美箱板紙漲價(PCA/IP/SW)、紙廠永久關廠 | https://www.packagingdive.com/ |
| `SRC_US_IP` | International Paper IR | 甲 | HTML_SCRAPE | Pine Hill 廠關閉、9/1 +$80/噸箱板紙調價 | https://www.internationalpaper.com/investors |
| `SRC_US_SW` | Smurfit WestRock IR | 甲 | HTML_SCRAPE | 合併後財報、歐洲 +€120 調價、折疊彩盒整合 | https://www.smurfitwestrock.com/investors |
| `SRC_US_PCA` | Packaging Corp of America | 甲 | HTML_SCRAPE | +$140/噸歷史級箱板紙漲價、出貨率 | https://ir.packagingcorp.com/ |
| `SRC_US_GPI` | Graphic Packaging Intl IR | 甲 | HTML_SCRAPE | 食品塗佈紙板、CRB/SBS廢紙基彩盒產能 | https://investors.graphicpkg.com/ |

### 5. 歐洲 (Europe, EU)

| 來源 ID | 機構名稱 | 分級 | 存取方式 | 主要揭露內容 | 網址 / 點位 |
|---|---|---|---|---|---|
| `SRC_EU_EURLEX` | 歐盟 EUR-Lex 法規公報 | 甲 | HTML_SCRAPE | PPWR Regulation 2025/40, PFAS 25ppb, BPA 2024/3190 | https://eur-lex.europa.eu/ |
| `SRC_EU_ECHA` | 歐洲化學品管理局 (ECHA) | 甲 | HTML_SCRAPE | PFHxA 限制條款、食品包裝化學物質限制清單 | https://echa.europa.eu/ |
| `SRC_EU_STORAENSO` | Stora Enso IR | 甲 | HTML_SCRAPE | Oulu 55 萬噸消費紙板投產、Skutskär 絨毛漿轉型 | https://www.storaenso.com/en/investors |
| `SRC_EU_UPM` | UPM-Kymmene IR | 甲 | HTML_SCRAPE | 烏拉圭 Paso de los Toros 漿廠放量、WISA 掛牌 | https://www.upm.com/investors/ |
| `SRC_EU_MONDI` | Mondi Group IR | 甲 | HTML_SCRAPE | Schumacher Packaging 收購案、瓦楞紙與食品紙袋 | https://www.mondigroup.com/investors/ |

### 6. 全球巨型漿廠 (Global Pulp Giants, GLOBAL)

| 來源 ID | 機構名稱 | 分級 | 存取方式 | 主要揭露內容 | 網址 / 點位 |
|---|---|---|---|---|---|
| `SRC_GLOBAL_SUZANO` | Suzano S.A. (巴西) | 甲 | SEC_EDGAR | Cerrado 255萬噸短纖漿淨價($562/噸)、出口月報 | https://ir.suzano.com.br/ |
| `SRC_GLOBAL_ARAUCO` | Arauco (智利) | 甲 | HTML_SCRAPE | MAPA 專案產能、亞洲漂針漿/漂闊漿外盤牌價 | https://www.arauco.com/en/investors/ |
| `SRC_GLOBAL_KLABIN` | Klabin S.A. (巴西) | 甲 | HTML_SCRAPE | Puma II 塗佈白卡與 Klabin 紙漿產能 | https://ri.klabin.com.br/en/ |
| `SRC_GLOBAL_CMPC` | CMPC (智利) | 甲 | HTML_SCRAPE | 智利與巴西木漿產量、亞洲牌價 | https://ir.cmpc.com/ |
| `SRC_GLOBAL_MERCER` | Mercer International IR | 甲 | SEC_EDGAR | 德國與北美 NBSK 長纖漿產能與現金成本 | https://www.mercerint.com/investors/ |

---

## 四、管道過濾與品管紀錄 (Audit & QC Log)

1. **日期驗證閘門**：所有抓取新聞發布日期必須與系統時間比對，若超過 30 天則自動標記為過期剔除（例如成功攔截 2021 年舊報導）。
2. **單一丙級來源攔截**：未獲得甲級（官網/申報）或乙級（Fastmarkets/卓創/生意社）佐證之丙級訊息，禁止直接進入報告產出。
3. **運算日誌存證**：每次 Pipeline 執行自動寫入 SQLite `pipeline_logs`，包含 ingested count, error count 與狀態摘要。
