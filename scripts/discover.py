
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

with open("config/sources.json", encoding="utf-8") as f:
    config = json.load(f)

def request_json(url, headers=None, data=None):
    req = urllib.request.Request(
        url, headers=headers or {}, data=data
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

# Twitch App Access Token automatisch anfordern
token_data = urllib.parse.urlencode({
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "client_credentials"
}).encode()

token = request_json(
    "https://id.twitch.tv/oauth2/token",
    data=token_data
)["access_token"]

headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {token}"
}

now = datetime.now(timezone.utc)
start = now - timedelta(hours=24)

def utc_string(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

results = []

for streamer in config["streamers"]:
    username = streamer["username"]

    user_url = (
        "https://api.twitch.tv/helix/users?"
        + urllib.parse.urlencode({"login": username})
    )
    users = request_json(user_url, headers)["data"]

    if not users:
        print(f"Streamer nicht gefunden: {username}")
        continue

    broadcaster_id = users[0]["id"]

    params = urllib.parse.urlencode({
        "broadcaster_id": broadcaster_id,
        "started_at": utc_string(start),
        "ended_at": utc_string(now),
        "first": 100
    })

    clips_url = "https://api.twitch.tv/helix/clips?" + params
    clips = request_json(clips_url, headers)["data"]

    for clip in clips:
        title = clip["title"]

        if not any(
            keyword.lower() in title.lower()
            for keyword in config["keywords"]
        ):
            continue

        results.append({
            "id": clip["id"],
            "title": title,
            "url": clip["url"],
            "streamer": username,
            "views": clip["view_count"],
            "created_at": clip["created_at"],
            "permission": streamer["permission"]
        })

results.sort(
    key=lambda item: item["views"],
    reverse=True
)

Path("output").mkdir(exist_ok=True)

with open("output/discovered_clips.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"{len(results)} passende Twitch-Clips gefunden.")
for clip in results[:10]:
    print(clip["title"], clip["url"])
