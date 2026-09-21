/**
 * Paperluz 雙語電子報雲端訂閱接收與即時迎新發信端點 (Google Apps Script)
 * ========================================================================
 * 
 * 功能：
 *   1. 接收 waatax.github.io/Paper/ 前端提交的訂閱請求 (POST)。
 *   2. 自動將訂閱者寫入 Google 試算表（自動分流 Subscribers_ZH 與 Subscribers_EN 兩分頁）。
 *   3. 幾秒內自動為訂閱者發送【即時迎新確認信】(含第 008 期報告與 A4 PDF 下載連結)。
 * 
 * 部署指引 (僅需 1 分鐘)：
 *   1. 前往 Google Drive 建立一個新的「Google 試算表」（命名為 Paperluz_Subscribers）。
 *   2. 點選上方選單「擴充功能」->「Apps Script」。
 *   3. 將本檔案全部程式碼複製貼上至 Apps Script 編輯器中。
 *   4. 點擊右上角「部署」->「新增部署作業」：
 *      - 種類選擇：「網頁應用程式 (Web App)」
 *      - 執行身分：「我」
 *      - 存取權限：「所有人 (Anyone)」
 *   5. 複製產生的「網頁應用程式網址」(例如 https://script.google.com/macros/s/.../exec)。
 *   6. 將該網址貼入 index.html 與 EN/index.html 的 NEWSLETTER_CONFIG.webhookUrl 即可全面生效！
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
    
    // 1. 寫入 Google 試算表分頁
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = (lang === "en") ? "Subscribers_EN" : "Subscribers_ZH";
    var sheet = ss.getSheetByName(sheetName);
    
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      sheet.appendRow(["Email", "Company", "Subscribed_At", "Language", "Status", "Source"]);
      sheet.getRange("A1:F1").setFontWeight("bold").setBackground("#131f3d").setFontColor("#ffffff");
    }
    
    // 檢查是否已重複訂閱
    var dataRange = sheet.getDataRange().getValues();
    var alreadyExists = false;
    for (var i = 1; i < dataRange.length; i++) {
      if (dataRange[i][0] && dataRange[i][0].toLowerCase() === email) {
        alreadyExists = true;
        break;
      }
    }
    
    if (!alreadyExists) {
      sheet.appendRow([email, company, timestamp, lang, "active", "github_pages_portal"]);
    }
    
    // 2. 即時透過 GmailApp 自動寄出迎新確認信 (包含最新期數與 PDF)
    sendInstantWelcomeEmail(email, lang, company);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Subscribed successfully and welcome email dispatched!",
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

function sendInstantWelcomeEmail(toEmail, lang, company) {
  var baseUrl = "https://waatax.github.io/Paper";
  var issueNum = "008";
  var pubDate = "2026-09-18";
  
  if (lang === "en") {
    var subject = "🎉 Welcome to Paperluz Weekly Intelligence! Your Issue 008 Package";
    var webUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + "_EN.html";
    var pdfUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + "_EN.pdf";
    var htmlBody = ""
      + "<div style='background-color:#0b1329; color:#f8fafc; font-family:sans-serif; padding:24px; max-width:600px; margin:auto; border-radius:12px; border:1px solid #24355a;'>"
      + "<h2 style='color:#60a5fa;'>📑 Paperluz Intelligence Hub</h2>"
      + "<h3 style='color:#ffffff;'>Welcome to Paperluz Executive Briefing!</h3>"
      + "<p>You are now subscribed to our <b>English Global Edition</b>. Every Friday at 07:00 AM (UTC+8), our curated report will be delivered directly to your inbox.</p>"
      + "<div style='background:#131f3d; padding:16px; border-radius:8px; margin:20px 0; border:1px solid #24355a;'>"
      + "<div style='color:#f59e0b; font-size:12px; font-weight:bold;'>🎁 COMPLIMENTARY WELCOME GIFT</div>"
      + "<h4 style='color:#ffffff; margin:6px 0 10px 0;'>Latest Release: Issue " + issueNum + " (" + pubDate + ")</h4>"
      + "<p style='font-size:13px; color:#94a3b8;'>Covering Brent Crude at $93.90, China NBSK at USD 690/MT, US OCC #11 export indices, and the North American Raw Spread $840 peak.</p>"
      + "<a href='" + webUrl + "' style='display:inline-block; background:#2563eb; color:#ffffff; padding:10px 16px; border-radius:6px; text-decoration:none; font-weight:bold; margin-right:8px;'>Read Online ➔</a>"
      + "<a href='" + pdfUrl + "' style='display:inline-block; background:#1e293b; color:#ffffff; border:1px solid #334155; padding:10px 16px; border-radius:6px; text-decoration:none; font-weight:bold;'>Download A4 PDF</a>"
      + "</div>"
      + "<p style='font-size:12px; color:#64748b;'>Published by Luznet / Paperluz Intelligence Center · https://waatax.github.io/Paper/EN/</p>"
      + "</div>";
  } else {
    var subject = "🎉 感謝訂閱 Paperluz 全球紙業情報週報！這是您的迎新專屬資料包";
    var webUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + ".html";
    var pdfUrl = baseUrl + "/Reports/PaperLuz-" + issueNum + "_" + pubDate + ".pdf";
    var htmlBody = ""
      + "<div style='background-color:#0b1329; color:#f8fafc; font-family:sans-serif; padding:24px; max-width:600px; margin:auto; border-radius:12px; border:1px solid #24355a;'>"
      + "<h2 style='color:#60a5fa;'>📑 Paperluz 台灣紙業產業情報平台</h2>"
      + "<h3 style='color:#ffffff;'>🎉 感謝您訂閱 Paperluz 每週產業情報！</h3>"
      + "<p>您好！歡迎加入 Paperluz 高階決策網絡。您已成功登記訂閱 <b>繁體中文版每週週報</b>。固定於 <b>每週五晨間 07:00 (UTC+8 台灣時間)</b> 準時自動發送當週最新報告。</p>"
      + "<div style='background:#131f3d; padding:16px; border-radius:8px; margin:20px 0; border:1px solid #24355a;'>"
      + "<div style='color:#f59e0b; font-size:12px; font-weight:bold;'>🎁 迎新專屬資料禮包</div>"
      + "<h4 style='color:#ffffff; margin:6px 0 10px 0;'>最新出刊：第 " + issueNum + " 期 (" + pubDate + ") 深度專題完整版</h4>"
      + "<p style='font-size:13px; color:#94a3b8;'>包含最新國際原油 $93.90/桶、中國進口針葉漿 NBSK USD 690/噸、美廢 11# 出口價與北美工紙 Raw Spread $840 歷史極限點。</p>"
      + "<a href='" + webUrl + "' style='display:inline-block; background:#2563eb; color:#ffffff; padding:10px 16px; border-radius:6px; text-decoration:none; font-weight:bold; margin-right:8px;'>在線閱讀第 " + issueNum + " 期 ➔</a>"
      + "<a href='" + pdfUrl + "' style='display:inline-block; background:#1e293b; color:#ffffff; border:1px solid #334155; padding:10px 16px; border-radius:6px; text-decoration:none; font-weight:bold;'>下載 A4 PDF 交付檔</a>"
      + "</div>"
      + "<p style='font-size:12px; color:#64748b;'>發行機構：光網資訊 Luznet ∕ Paperluz 產業情報中心 · https://waatax.github.io/Paper/</p>"
      + "</div>";
  }
  
  MailApp.sendEmail({
    to: toEmail,
    subject: subject,
    htmlBody: htmlBody
  });
}
