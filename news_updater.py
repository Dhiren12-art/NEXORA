
import os
import re
import html
import time
import requests
import feedparser

from html.parser import HTMLParser
from urllib.parse import urljoin
from datetime import datetime, timezone

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

FEEDS = {
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "BBC India": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss"
}

session = requests.Session()
session.headers.update({
    "User-Agent": "NEXORA-NewsBot/1.0"
})

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()

def valid_image(url, base=None):
    if not url:
        return None
    url = html.unescape(str(url)).strip()
    if url.startswith("//"):
        url = "https:" + url
    if base:
        url = urljoin(base, url)
    if not url.startswith(("https://", "http://")):
        return None
    if any(x in url.lower() for x in ["pixel", "tracker", "spacer.gif"]):
        return None
    return url


def get_image(entry, link):
    candidates = []

    # Prefer full-size media images over thumbnails
    for field in ["media_content", "media_thumbnail"]:
        items = entry.get(field, []) or []
        if isinstance(items, dict):
            items = [items]

        for item in items:
            if isinstance(item, dict):
                image = valid_image(item.get("url"), link)
                if image:
                    try:
                        width = int(item.get("width", 0))
                        height = int(item.get("height", 0))
                    except (TypeError, ValueError):
                        width = height = 0

                    candidates.append((width * height, image))

    # Use the largest available image
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    # Check image links in the RSS entry
    for item in entry.get("links", []) or []:
        if item.get("type", "").startswith("image/"):
            image = valid_image(item.get("href"), link)
            if image:
                return image

    # Check the RSS summary for an image
    summary = entry.get("summary", "")
    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        summary,
        re.I
    )
    if match:
        return valid_image(match.group(1), link)

    # Last option: publisher's social preview image
    try:
        response = session.get(link, timeout=12)
        response.raise_for_status()

        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, response.text, re.I)
            if match:
                return valid_image(match.group(1), response.url)

    except Exception as error:
        print("Image lookup:", error)

    return None


SPORT_KEYWORDS = [
    "cricket", "ipl", "t20", "odi", "test match",
    "football", "soccer", "tennis", "badminton",
    "hockey", "basketball", "wrestling", "boxing",
    "world cup", "champions trophy", "premier league",
    "wpl", "wbbL", "ashes", "fifa", "olympics",
    "match result", "playing xi", "innings",
    "wicket", "batter", "bowler"
]

def is_sports_story(title, summary):
    text = (title + " " + summary).lower()
    return any(word in text for word in SPORT_KEYWORDS)
    
def published(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(
            time.mktime(parsed), timezone.utc
        ).isoformat()
    return datetime.now(timezone.utc).isoformat()

def main():
    articles = []

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:12]:
                title = clean_text(entry.get("title"))
                link = entry.get("link")

                if not title or not link:
                    continue

                summary_text = clean_text(entry.get("summary", ""))

                if is_sports_story(title, summary_text):
                    print("SKIPPED SPORTS:", title)
                    continue

                image = get_image(entry, link)

                article = {
                    "title": title,
                    "summary": clean_text(
                        entry.get("summary", "")
                    )[:1200],
                    "source_name": source,
                    "source_url": link,
                    "published_at": published(entry)
                }

                if image:
                    article["image_url"] = image
                    print("IMAGE FOUND:", title)

                articles.append(article)

        except Exception as error:
            print("FEED ERROR:", source, error)
    unique_articles = {}
    for article in articles:
        unique_articles[article["source_url"]] = article

    articles = list(unique_articles.values())
    if not articles:
        raise SystemExit("No articles fetched.")

    response = session.post(
        f"{SUPABASE_URL}/rest/v1/news_feed",
        params={"on_conflict": "source_url"},
        headers={
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal"
        },
        json=articles,
        timeout=40
    )

    print("SUPABASE:", response.text)
    response.raise_for_status()

    print("SUCCESS:", len(articles), "articles processed.")

if __name__ == "__main__":
    main()
      
