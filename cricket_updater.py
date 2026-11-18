
import os
import re
import html
import time
import requests
import feedparser
from datetime import datetime, timezone

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

FEEDS = {
    "BBC Sport Cricket": "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "ESPNcricinfo": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
}

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()

def get_image(entry):
    media = entry.get("media_thumbnail", [])
    if media:
        return media[0].get("url")

    media = entry.get("media_content", [])
    if media:
        return media[0].get("url")

    for item in entry.get("links", []):
        if item.get("type", "").startswith("image/"):
            return item.get("href")

    return None

def get_published(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(
            time.mktime(parsed), timezone.utc
        ).isoformat()

    return datetime.now(timezone.utc).isoformat()

def main():
    articles = []

    for source, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:15]:
                title = clean_text(entry.get("title"))
                link = entry.get("link")

                if not title or not link:
                    continue

                articles.append({
                    "title": title,
                    "summary": clean_text(
                        entry.get("summary", "")
                    )[:1000],
                    "source_name": source,
                    "source_url": link,
                    "image_url": get_image(entry),
                    "published_at": get_published(entry)
                })

        except Exception as error:
            print(f"Feed error ({source}): {error}")

    if not articles:
        print("No cricket articles found.")
        return

    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/cricket_feed",
        params={"on_conflict": "source_url"},
        headers={
            "apikey": SUPABASE_KEY,
        
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal"
        },
        json=articles,
        timeout=30
    )
print("SUPABASE RESPONSE:", response.text)
    response.raise_for_status()
    print(f"Successfully processed {len(articles)} cricket articles.")

if __name__ == "__main__":
    main()
  
