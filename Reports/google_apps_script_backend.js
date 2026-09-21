/**
 * Paperluz 雙語電子報雲端訂閱接收與【即時雙發】端點 (Google Apps Script)
 * ========================================================================
 * 
 * 核心業務邏輯：
 *   1. 接收 waatax.github.io/Paper/ 前端提交的訂閱請求 (POST)。
 *   2. 自動將訂閱者寫入 Google 試算表（自動分流 Subscribers_ZH 與 Subscribers_EN 兩分頁，去重儲存）。
 *   3. 【立刻發出一封歡迎信】：確認訂閱成功、說明每週五 07:00 出刊時程、四大核心功能與會員權益。
 *   4. 【立刻寄出目前最新一期的電子報】：即時發送最新第 008 期 (2026-09-18) 完整深度週報 (含行情表、四大洞察與 PDF 下載連結)。
 * 
 * 部署指引 (僅需 1 分鐘)：
 *   1. 前往 Google Drive 建立一個新的「Google 試算表」（命名為 Paperluz_Subscribers）。
 *   2. 點選上方選單「擴充功能」->「Apps Script」。
 *   3. 將本檔案全部程式碼複製貼上至 Apps Script 編輯器中覆蓋。
 *   4. 點擊右上角「部署」->「新增部署作業」：
 *      - 種類選擇：「網頁應用程式 (Web App)」
 *      - 執行身分：「我 (您的 Google 帳號)」
 *      - 存取權限：「所有人 (Anyone)」
 *   5. 複製產生的「網頁應用程式網址」(例如 https://script.google.com/macros/s/.../exec)。
 *   6. 將該網址貼入 index.html 與 EN/index.html 的 NEWSLETTER_CONFIG.webhookUrl，立即全面生效！
 */

function doPost(e) {
  try {
    var contents = e.postData.contents;
    var data = JSON.parse(contents);
    
    var email = (data.email || "").trim().toLowerCase();
    var company = (data.company || "").trim();
    var lang = (data.language || "zh").trim().toLowerCase();
    var timestamp = data.timestamp || new Date().toISOString();
    
    if (!email || email.indexOf("@") === -1) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Invalid email address"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 1. 寫入 Google 試算表分頁 (自動去重)
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = (lang === "en") ? "Subscribers_EN" : "Subscribers_ZH";
    var sheet = ss.getSheetByName(sheetName);
    
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      sheet.appendRow(["Email", "Company", "Subscribed_At", "Language", "Status", "Source"]);
      sheet.getRange("A1:F1").setFontWeight("bold").setBackground("#131f3d").setFontColor("#ffffff");
    }
    
    var dataRange = sheet.getDataRange().getValues();
    var alreadyExists = false;
    for (var i = 1; i < dataRange.length; i++) {
      if (dataRange[i][0] && dataRange[i][0].toLowerCase() === email) {
        alreadyExists = true;
        break;
      }
    }
    
    if (!alreadyExists) {
      sheet.appendRow([email, company, timestamp, lang, "active", "paperluz_web_portal"]);
    }
    
    // 2. 【第一封：立即發出專屬歡迎信】
    sendWelcomeEmail(email, lang, company);
    
    // 3. 【第二封：立刻寄出目前最新一期完整電子報 (Issue 008)】
    Utilities.sleep(800); // 間隔 0.8 秒確保收發信序
    sendLatestIssueNewsletter(email, lang, company);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Subscribed successfully! Welcome email and latest issue have been dispatched.",
      email: email,
      language: lang
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// ─────────────────────────────────────────────────────────────
// 第一封：專屬歡迎信 (Welcome Email)
// ─────────────────────────────────────────────────────────────
function sendWelcomeEmail(toEmail, lang, company) {
  var baseUrl = "https://waatax.github.io/Paper";
  var issueNum = "008";
  var pubDate = "2026-09-18";
  
  if (lang === "en") {
    var subject = "🎉 Welcome to Paperluz Intelligence Network (Subscription & Member Guide)";
    var portalUrl = baseUrl + "/EN/";
    var htmlBody = ""
      + "<!DOCTYPE html><html><body style='margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, Roboto, sans-serif;'>"
      + "<div style='max-width:620px; margin:20px auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; color:#f8fafc;'>"
      + "  <div style='background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:24px 28px; border-bottom:1px solid #24355a;'>"
      + "    <h2 style='color:#ffffff; margin:0 0 4px 0; font-size:22px;'>📑 Paperluz Intelligence Hub</h2>"
      + "    <div style='color:#60a5fa; font-size:13px; font-weight:600;'>Global Pulp & Paper Executive Decision Network</div>"
      + "  </div>"
      + "  <div style='padding:26px 28px;'>"
      + "    <h3 style='color:#ffffff; font-size:18px; margin-top:0;'>Welcome to Paperluz Weekly Briefing!</h3>"
      + "    <p style='color:#cbd5e1; font-size:14px; line-height:1.7;'>"
      + "      Thank you for subscribing" + (company ? (" on behalf of <strong>" + company + "</strong>") : "") + ". "
      + "      You are officially registered for the <strong>Paperluz English Global Intelligence Edition</strong>."
      + "    </p>"
      + "    <div style='background:#0b1329; border-left:4px solid #3b82f6; border-radius:6px; padding:14px 18px; margin:20px 0; font-size:13.5px; color:#94a3b8; line-height:1.6;'>"
      + "      <strong style='color:#ffffff;'>📬 Regular Delivery Schedule:</strong><br>"
      + "      Every <strong>Friday morning at 07:00 AM (UTC+8)</strong>, you will receive our curated weekly intelligence briefing directly in your inbox."
      + "    </div>"
      + "    <h4 style='color:#ffffff; font-size:14px; margin:20px 0 10px 0;'>✨ What You Can Expect:</h4>"
      + "    <ul style='color:#94a3b8; font-size:13px; line-height:1.7; padding-left:18px;'>"
      + "      <li><strong>Commodity Pricing Matrix:</strong> Brent crude, NBSK, BHKP, US OCC #11 export indices.</li>"
      + "      <li><strong>Real-time Margin Simulator:</strong> Linerboard spread calculations vs. raw material spikes.</li>"
      + "      <li><strong>Global Regulatory Radar:</strong> EUDR, PPWR, REACH PFHxA compliance trackers.</li>"
      + "      <li><strong>Executive Takeaways:</strong> Curated strategic insights for paper mills and converting plants.</li>"
      + "    </ul>"
      + "    <div style='background:#1a294f; border-radius:8px; padding:16px; margin-top:24px; border:1px solid #24355a;'>"
      + "      <div style='color:#f59e0b; font-size:12px; font-weight:bold;'>💡 INCOMING LATEST REPORT</div>"
      + "      <p style='color:#cbd5e1; font-size:13px; margin:6px 0 0 0;'>"
      + "        We have also immediately dispatched <strong>Issue " + issueNum + " (" + pubDate + ")</strong> to your inbox in a separate message. Feel free to explore our portal anytime below."
      + "      </p>"
      + "    </div>"
      + "    <div style='text-align:center; margin-top:24px;'>"
      + "      <a href='" + portalUrl + "' style='display:inline-block; background:#2563eb; color:#ffffff; padding:11px 22px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13.5px;'>Visit Paperluz Global Portal ➔</a>"
      + "    </div>"
      + "  </div>"
      + "  <div style='background:#0b1329; border-top:1px solid #24355a; padding:16px 28px; text-align:center; color:#64748b; font-size:11.5px;'>"
      + "    Paperluz · Global Intelligence Hub · Published by Luznet"
      + "  </div>"
      + "</div></body></html>";
  } else {
    var subject = "🎉 歡迎加入 Paperluz 全球紙業情報網絡（訂閱確認與權益指南）";
    var portalUrl = baseUrl + "/";
    var htmlBody = ""
      + "<!DOCTYPE html><html><body style='margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, Roboto, sans-serif;'>"
      + "<div style='max-width:620px; margin:20px auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; color:#f8fafc;'>"
      + "  <div style='background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:24px 28px; border-bottom:1px solid #24355a;'>"
      + "    <h2 style='color:#ffffff; margin:0 0 4px 0; font-size:22px;'>📑 Paperluz 台灣與全球紙業產業情報平台</h2>"
      + "    <div style='color:#60a5fa; font-size:13px; font-weight:600;'>光網資訊 Luznet ∕ 產業決策智庫</div>"
      + "  </div>"
      + "  <div style='padding:26px 28px;'>"
      + "    <h3 style='color:#ffffff; font-size:18px; margin-top:0;'>🎉 感謝您訂閱 Paperluz 產業情報週報！</h3>"
      + "    <p style='color:#cbd5e1; font-size:14px; line-height:1.7;'>"
      + "      您好！歡迎加入 Paperluz 高階決策名冊" + (company ? ("（" + company + "）") : "") + "。"
      + "      您已成功完成 <strong>繁體中文版每週週報</strong> 的登記訂閱。"
      + "    </p>"
      + "    <div style='background:#0b1329; border-left:4px solid #3b82f6; border-radius:6px; padding:14px 18px; margin:20px 0; font-size:13.5px; color:#94a3b8; line-height:1.6;'>"
      + "      <strong style='color:#ffffff;'>📬 固定出刊與派發日程：</strong><br>"
      + "      每週固定於 <strong>每週五晨間 07:00 (UTC+8 台灣時間)</strong> 準時發送當週最新報告至您的電子信箱。"
      + "    </div>"
      + "    <h4 style='color:#ffffff; font-size:14px; margin:20px 0 10px 0;'>✨ 專屬情報核心板塊：</h4>"
      + "    <ul style='color:#94a3b8; font-size:13px; line-height:1.7; padding-left:18px;'>"
      + "      <li><strong>大宗原料即時行情：</strong> 國際原油、進口針葉漿 NBSK、闊葉漿 BHKP、美廢 11#。</li>"
      + "      <li><strong>工紙利差動態試算：</strong> 工紙對廢紙 Raw Spread 歷史極限點監測。</li>"
      + "      <li><strong>全球法規與政策雷達：</strong> 歐盟 PPWR、EUDR、REACH PFHxA 禁用過渡期倒數。</li>"
      + "      <li><strong>四大決策洞察：</strong> 造紙停機保價、南美港口直航護城河、紙箱廠轉嫁壓力評估。</li>"
      + "    </ul>"
      + "    <div style='background:#1a294f; border-radius:8px; padding:16px; margin-top:24px; border:1px solid #24355a;'>"
      + "      <div style='color:#f59e0b; font-size:12px; font-weight:bold;'>💡 隨信即刻附送最新一期報告</div>"
      + "      <p style='color:#cbd5e1; font-size:13px; margin:6px 0 0 0;'>"
      + "        系統已同步為您寄出 <strong>第 " + issueNum + " 期 (" + pubDate + ") 完整週報</strong>。若您希望即刻在瀏覽器瀏覽，歡迎點擊下方按鈕。"
      + "      </p>"
      + "    </div>"
      + "    <div style='text-align:center; margin-top:24px;'>"
      + "      <a href='" + portalUrl + "' style='display:inline-block; background:#2563eb; color:#ffffff; padding:11px 22px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13.5px;'>開啟 Paperluz 產業情報大廳 ➔</a>"
      + "    </div>"
      + "  </div>"
      + "  <div style='background:#0b1329; border-top:1px solid #24355a; padding:16px 28px; text-align:center; color:#64748b; font-size:11.5px;'>"
      + "    發行機構：光網資訊 Luznet ∕ Paperluz 產業情報中心"
      + "  </div>"
      + "</div></body></html>";
  }
  
  MailApp.sendEmail({
    to: toEmail,
    subject: subject,
    htmlBody: htmlBody
  });
}

// ─────────────────────────────────────────────────────────────
// 第二封：立刻寄出目前最新一期的完整電子報 (Latest Issue Newsletter)
// ─────────────────────────────────────────────────────────────
function sendLatestIssueNewsletter(toEmail, lang, company) {
  var baseUrl = "https://waatax.github.io/Paper";
  var issueNum = "008";
  var pubDate = "2026-09-18";
  
  if (lang === "en") {
    var subject = "📑 [Latest Issue] Paperluz Weekly Industry Intelligence Issue " + issueNum + " (" + pubDate + ")";
    var webUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + "_EN.html";
    var pdfUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + "_EN.pdf";
    var portalUrl = baseUrl + "/EN/";
    
    var htmlBody = ""
      + "<!DOCTYPE html><html><body style='margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, Roboto, sans-serif;'>"
      + "<div style='max-width:640px; margin:20px auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; color:#f8fafc;'>"
      + "  <div style='background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:24px 28px; border-bottom:1px solid #24355a;'>"
      + "    <div style='font-size:12px; font-weight:700; color:#93c5fd; text-transform:uppercase;'>Paperluz Weekly Dispatch · Issue " + issueNum + "</div>"
      + "    <h1 style='color:#ffffff; font-size:21px; margin:8px 0 4px 0;'>Global Pulp & Paper Industry Intelligence Briefing</h1>"
      + "    <div style='color:#60a5fa; font-size:13px;'>Curated Market Trends · Commodity Tracking · Mill Margins · Regulatory Radar</div>"
      + "  </div>"
      + "  <div style='padding:24px 28px;'>"
      + "    <div style='background:#0b1329; border-radius:8px; padding:14px 18px; margin-bottom:20px; border:1px solid #24355a; font-size:13px; color:#cbd5e1; line-height:1.6;'>"
      + "      <strong>Executive Overview (" + pubDate + "):</strong> Crude oil consolidates near $94/bbl; China NBSK holds firm at $690/MT; US OCC #11 export price steady at $135; North American raw spread touches historic $840 peak."
      + "    </div>"
      + "    <h3 style='color:#ffffff; font-size:15px; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:12px;'>📊 Key Commodity & Benchmark Indicators</h3>"
      + "    <table style='width:100%; border-collapse:collapse; font-size:13px; margin-bottom:24px;'>"
      + "      <tr style='background:#1a294f; color:#94a3b8; text-align:left; font-size:12px;'><th style='padding:8px 10px;'>Commodity / Index</th><th style='padding:8px 10px;'>Spot Price</th><th style='padding:8px 10px;'>Interpretation</th></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>Brent Crude Oil</td><td style='padding:8px 10px; color:#ef4444; font-weight:bold;'>$93.90 / bbl</td><td style='padding:8px 10px; color:#94a3b8;'>Geopolitical tension high</td></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>China NBSK Import</td><td style='padding:8px 10px; color:#60a5fa; font-weight:bold;'>USD 690 / MT</td><td style='padding:8px 10px; color:#94a3b8;'>RMB 4,900 · Bottom forming</td></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>US OCC #11 Waste Paper</td><td style='padding:8px 10px; color:#f59e0b; font-weight:bold;'>$135 / short ton</td><td style='padding:8px 10px; color:#94a3b8;'>Asian import CIF stabilized</td></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>NA Raw Spread</td><td style='padding:8px 10px; color:#a78bfa; font-weight:bold;'>$840 Peak</td><td style='padding:8px 10px; color:#94a3b8;'>All 3 price hikes in effect</td></tr>"
      + "      <tr><td style='padding:8px 10px; font-weight:bold;'>EU PFHxA Ban</td><td style='padding:8px 10px; color:#ef4444; font-weight:bold;'>T-30 Days</td><td style='padding:8px 10px; color:#94a3b8;'>Takes effect Oct 18, 2026</td></tr>"
      + "    </table>"
      + "    <h3 style='color:#ffffff; font-size:15px; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:12px;'>💡 Executive Strategic Insights</h3>"
      + "    <ul style='color:#cbd5e1; font-size:13px; line-height:1.7; padding-left:18px; margin-bottom:24px;'>"
      + "      <li><strong>Mill Downtime Discipline:</strong> Shanying and Nine Dragons schedule October downtime to curb excess supply and defend recent RMB 30-50/ton price increases.</li>"
      + "      <li><strong>South American Logistics Moat:</strong> CMPC seals a 25-year, $370M deepwater terminal contract in Rio Grande, joining Suzano in controlling transatlantic pulp corridors.</li>"
      + "      <li><strong>Linerboard Spread at Extremes:</strong> North American raw spread hits $840/ton, creating peak margins for integrated mills but squeezing independent converters.</li>"
      + "      <li><strong>PFHxA Phase-out Deadline:</strong> Food contact packaging faces zero tolerance for perfluorohexanoic acid starting Oct 18; barrier paper order surge observed.</li>"
      + "    </ul>"
      + "    <div style='text-align:center; padding:14px 0;'>"
      + "      <a href='" + webUrl + "' style='display:inline-block; background:#2563eb; color:#ffffff; padding:12px 22px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13.5px; margin-right:8px;'>Read Issue " + issueNum + " Online ➔</a>"
      + "      <a href='" + pdfUrl + "' style='display:inline-block; background:#0b1329; color:#f8fafc; border:1px solid #334155; padding:12px 22px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13.5px;'>Download A4 PDF</a>"
      + "    </div>"
      + "  </div>"
      + "  <div style='background:#0b1329; border-top:1px solid #24355a; padding:18px 28px; text-align:center; color:#64748b; font-size:11.5px;'>"
      + "    Paperluz · Published by Luznet / Paperluz Intelligence Center · <a href='" + portalUrl + "' style='color:#3b82f6;'>waatax.github.io/Paper/EN/</a>"
      + "  </div>"
      + "</div></body></html>";
  } else {
    var subject = "📑【最新出刊】Paperluz 紙業情報週報 第 " + issueNum + " 期 (" + pubDate + ")";
    var webUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + ".html";
    var pdfUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + ".pdf";
    var portalUrl = baseUrl + "/";
    
    var htmlBody = ""
      + "<!DOCTYPE html><html><body style='margin:0; padding:0; background-color:#0b1329; font-family:-apple-system, BlinkMacSystemFont, Roboto, sans-serif;'>"
      + "<div style='max-width:640px; margin:20px auto; background-color:#131f3d; border:1px solid #24355a; border-radius:12px; overflow:hidden; color:#f8fafc;'>"
      + "  <div style='background:linear-gradient(135deg, #1d4ed8 0%, #0b1329 100%); padding:24px 28px; border-bottom:1px solid #24355a;'>"
      + "    <div style='font-size:12px; font-weight:700; color:#93c5fd; text-transform:uppercase;'>Paperluz 週報即時派送 · 第 " + issueNum + " 期</div>"
      + "    <h1 style='color:#ffffff; font-size:21px; margin:8px 0 4px 0;'>全球與台灣紙業產業情報週報</h1>"
      + "    <div style='color:#60a5fa; font-size:13px;'>國際漿價走勢 · 工紙原料利差 · 能源海運波動 · 歐盟法規全景分析</div>"
      + "  </div>"
      + "  <div style='padding:24px 28px;'>"
      + "    <div style='background:#0b1329; border-radius:8px; padding:14px 18px; margin-bottom:20px; border:1px solid #24355a; font-size:13px; color:#cbd5e1; line-height:1.6;'>"
      + "      <strong>本週核心摘要 (" + pubDate + ")：</strong> 國際原油高位整固於 $93.90/桶；中國進口針葉漿 (NBSK) 美金報價穩在 USD 690/噸；美廢 11# 出口報價穩健於 $135/短噸；北美工紙 Raw Spread 站上 $840 歷史極限點。"
      + "    </div>"
      + "    <h3 style='color:#ffffff; font-size:15px; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:12px;'>📊 核心原物料與市場基準行情</h3>"
      + "    <table style='width:100%; border-collapse:collapse; font-size:13px; margin-bottom:24px;'>"
      + "      <tr style='background:#1a294f; color:#94a3b8; text-align:left; font-size:12px;'><th style='padding:8px 10px;'>商品 ∕ 指標</th><th style='padding:8px 10px;'>本週現貨價</th><th style='padding:8px 10px;'>走勢與利差解讀</th></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>布蘭特原油 (Brent)</td><td style='padding:8px 10px; color:#ef4444; font-weight:bold;'>$93.90 / 桶</td><td style='padding:8px 10px; color:#94a3b8;'>地緣高位整固 · 週跌 -0.3%</td></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>中國進口針葉漿 (NBSK)</td><td style='padding:8px 10px; color:#60a5fa; font-weight:bold;'>USD 690 / 噸</td><td style='padding:8px 10px; color:#94a3b8;'>RMB 4,900 · 築底態勢確立</td></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>美國 11# OCC 廢紙</td><td style='padding:8px 10px; color:#f59e0b; font-weight:bold;'>$135 / 美噸</td><td style='padding:8px 10px; color:#94a3b8;'>出口走堅 · 亞洲到港 CIF 穩定</td></tr>"
      + "      <tr style='border-bottom:1px solid #1a294f;'><td style='padding:8px 10px; font-weight:bold;'>北美工紙 Raw Spread</td><td style='padding:8px 10px; color:#a78bfa; font-weight:bold;'>$840 極限點</td><td style='padding:8px 10px; color:#94a3b8;'>三輪調價全數開票落地</td></tr>"
      + "      <tr><td style='padding:8px 10px; font-weight:bold;'>歐盟 PFHxA 禁令</td><td style='padding:8px 10px; color:#ef4444; font-weight:bold;'>倒數 30 天</td><td style='padding:8px 10px; color:#94a3b8;'>10/18 正式生效 · 禁絕全氟塗層</td></tr>"
      + "    </table>"
      + "    <h3 style='color:#ffffff; font-size:15px; border-bottom:1px solid #24355a; padding-bottom:8px; margin-bottom:12px;'>💡 本週 4 大決策洞察</h3>"
      + "    <ul style='color:#cbd5e1; font-size:13px; line-height:1.7; padding-left:18px; margin-bottom:24px;'>"
      + "      <li><strong>中國造紙停機保價自律：</strong> 山鷹與玖龍啟動秋季檢修，有效壓制庫存累積，力保每噸 RMB 30~50 提價成果。</li>"
      + "      <li><strong>南美木漿跨洋物流主權：</strong> 智利 CMPC 簽訂 25 年巴西 Rio Grande 深水碼頭專用合約，與 Suzano 形成跨洋雙雄護城河。</li>"
      + "      <li><strong>北美工紙利差極限：</strong> 原紙對廢紙利差達 $840/噸，下游獨立紙箱廠成本轉嫁壓力達峰值。</li>"
      + "      <li><strong>法規海嘯合規倒數：</strong> 歐盟 REACH PFHxA 限制條款 10/18 生效（僅剩 30 天），食品接觸紙禁絕全氟塗層。</li>"
      + "    </ul>"
      + "    <div style='text-align:center; padding:14px 0;'>"
      + "      <a href='" + webUrl + "' style='display:inline-block; background:#2563eb; color:#ffffff; padding:12px 22px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13.5px; margin-right:8px;'>在線閱讀第 " + issueNum + " 期完整報告 ➔</a>"
      + "      <a href='" + pdfUrl + "' style='display:inline-block; background:#0b1329; color:#f8fafc; border:1px solid #334155; padding:12px 22px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13.5px;'>下載 A4 PDF 交付檔</a>"
      + "    </div>"
      + "  </div>"
      + "  <div style='background:#0b1329; border-top:1px solid #24355a; padding:18px 28px; text-align:center; color:#64748b; font-size:11.5px;'>"
      + "    發行機構：光網資訊 Luznet ∕ Paperluz 產業情報中心 · <a href='" + portalUrl + "' style='color:#3b82f6;'>waatax.github.io/Paper/</a>"
      + "  </div>"
      + "</div></body></html>";
  }
  
  MailApp.sendEmail({
    to: toEmail,
    subject: subject,
    htmlBody: htmlBody
  });
}
