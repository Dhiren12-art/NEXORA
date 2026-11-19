
import json
import os
import time
import urllib.parse
import urllib.request

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def get_json(url, headers=None):
    request = urllib.request.Request(
        url,
        headers=headers or {
            "User-Agent": "NEXORA-PlayerPhotoUpdater/1.0"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def find_player_photo(player_name):
    search_url = (
        "https://en.wikipedia.org/w/rest.php/v1/search/page?"
        + urllib.parse.urlencode({
            "q": player_name,
            "limit": 10
        })
    )

    try:
        result = get_json(search_url)
        pages = result.get("pages", [])

        for page in pages:
            title = page.get("title", "").strip()

            if title.casefold() != player_name.strip().casefold():
                continue

            thumbnail = page.get("thumbnail") or {}
            photo_url = thumbnail.get("url")

            if photo_url:
                if photo_url.startswith("//"):
                    photo_url = "https:" + photo_url

                if photo_url.startswith("https://"):
                    return photo_url

        return None

    except Exception as error:
        print(f"Photo search failed for {player_name}: {error}")
        return None


def update_player_photo(player_id, photo_url):
    url = (
        f"{SUPABASE_URL}/rest/v1/players?"
        + urllib.parse.urlencode({"id": f"eq.{player_id}"})
    )

    headers = dict(HEADERS)
    headers["Prefer"] = "return=minimal"

    body = json.dumps({
        "profile_image": photo_url
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="PATCH"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status


def main():
    url = (
        f"{SUPABASE_URL}/rest/v1/players?"
        "select=id,full_name,profile_image&limit=1000"
    )

    players = get_json(url, HEADERS)

    print(f"Found {len(players)} players.")

    updated = 0
    skipped = 0

    for player in players:
        name = player.get("full_name")
        existing_photo = player.get("profile_image")

        if not name:
            skipped += 1
            continue

        if existing_photo and existing_photo.strip():
            print(f"Already has photo: {name}")
            skipped += 1
            continue

        print(f"Searching photo: {name}")

        photo_url = find_player_photo(name)

        if not photo_url:
            print(f"No exact matching photo found: {name}")
            skipped += 1
            continue

        try:
            update_player_photo(player["id"], photo_url)
            print(f"Photo added: {name}")
            updated += 1

        except Exception as error:
            print(f"Could not update {name}: {error}")

        time.sleep(1)

    print("-------------------------")
    print(f"Photos added: {updated}")
    print(f"Skipped: {skipped}")
    print("NEXORA photo updater finished.")


if __name__ == "__main__":
    main()
