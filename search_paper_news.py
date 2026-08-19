import urllib.request
import json
import xml.etree.ElementTree as ET
from datetime import datetime

def search_paper_news():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 啟動最新紙業新聞聚合引擎...")
    
    # 這裡使用各大紙業新聞 RSS Feed 或 API 作為示範
    feeds = {
        "RISI / Fastmarkets": "https://www.fastmarkets.com/feed/",
        "PaperAge": "https://www.paperage.com/feed",
        "Yahoo Finance (Suzano)": "https://finance.yahoo.com/rss/headline?s=SUZ",
        "Yahoo Finance (IP)": "https://finance.yahoo.com/rss/headline?s=IP"
    }
    
    for source, url in feeds.items():
        print(f"\n➤ 正在抓取: {source}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                
            try:
                root = ET.fromstring(content)
                items = root.findall('.//item')[:5] # 取前五筆
                if not items:
                    print("  查無最新新聞。")
                for item in items:
                    title = item.find('title').text if item.find('title') is not None else 'No Title'
                    pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    print(f"  - [{pubDate}] {title}")
            except ET.ParseError:
                print("  XML 解析失敗，可能是該來源目前不提供標準 RSS。")
                
        except Exception as e:
            print(f"  抓取失敗: {e}")

if __name__ == "__main__":
    search_paper_news()
