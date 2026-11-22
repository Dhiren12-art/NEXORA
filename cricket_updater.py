
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
    "BBC Sport Cricket": "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "ESPNcricinfo": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 NEXORA Cricket News Bot"
}

session = requests.Session()
session.headers.update(HEADERS)


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def valid_image_url(url, base_url=None):
    if not url:
        return None

    url = html.unescape(str(url)).strip()

    if url.startswith("//"):
        url = "https:" + url

    if base_url:
        url = urljoin(base_url, url)

    if not url.startswith(("https://", "http://")):
        return None

    if any(word in url.lower() for word in [
        "pixel", "tracker", "spacer.gif"
    ]):
        return None

    return url


def get_rss_image(entry, article_url):
    for field in ["media_thumbnail", "media_content"]:
        items = entry.get(field, []) or []

        if isinstance(items, dict):
            items = [items]

        for item in items:
            if isinstance(item, dict):
                image = valid_image_url(
                    item.get("url"), article_url
                )
                if image:
                    return image

    for item in entry.get("links", []) or []:
        if item.get("type", "").startswith("image/"):
            image = valid_image_url(
                item.get("href"), article_url
            )
            if image:
                return image

    fragments = [entry.get("summary", "")]

    for item in entry.get("content", []) or []:
        fragments.append(item.get("value", ""))

    for fragment in fragments:
        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            fragment or "",
            re.I
        )

        if match:
            image = valid_image_url(
                match.group(1), article_url
            )
            if image:
                return image

    return None


class ImageMetadataParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.image = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta" or self.image:
            return

        values = {
            key.lower(): value
            for key, value in attrs
            if key and value
        }

        property_name = (
            values.get("property")
            or values.get("name")
            or ""
        ).lower()

        if property_name in [
            "og:image",
            "og:image:url",
            "twitter:image",
            "twitter:image:src"
        ]:
            self.image = values.get("content")


def get_article_image(article_url):
    try:
        response = session.get(
            article_url,
            timeout=(5, 8)
        )

        response.raise_for_status()

        if "text/html" not in response.headers.get(
            "Content-Type", ""
        ).lower():
            return None

        parser = ImageMetadataParser()
        parser.feed(response.text[:500000])

        return valid_image_url(
            parser.image,
            response.url
        )

    except Exception as error:
        print("Image lookup failed:", error)
        return None


def get_published(entry):
    parsed = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
    )

    if parsed:
        return datetime.fromtimestamp(
            time.mktime(parsed),
            timezone.utc
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

                image_url = get_rss_image(entry, link)

                if not image_url:
                    image_url = get_article_image(link)

                if image_url:
                    print("IMAGE FOUND:", title)
                else:
                    print("NO IMAGE:", title)

                article = {
                    "title": title,
                    "summary": clean_text(
                        entry.get("summary", "")
                    )[:1000],
                    "source_name": source,
                    "source_url": link,
                    "published_at": get_published(entry)
                }

                # Never overwrite an existing image with null
                if image_url:
                    article["image_url"] = image_url

                articles.append(article)

        except Exception as error:
            print("Feed error:", source, error)

    if not articles:
        print("No cricket articles found.")
        return

    response = session.post(
        f"{SUPABASE_URL}/rest/v1/cricket_feed",
        params={"on_conflict": "source_url"},
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal"
        },
        json=articles,
        timeout=30
    )

    print("SUPABASE RESPONSE:", response.text)
    response.raise_for_status()

    print("Successfully processed", len(articles), "articles.")


if __name__ == "__main__":
    main()
        
