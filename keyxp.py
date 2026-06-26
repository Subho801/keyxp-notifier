import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from discord_webhook import DiscordWebhook, DiscordEmbed

URL = "https://keyxp.co/giveaway"
DATA_FILE = "keyxp_last.json"
WEBHOOK = os.getenv("WEBHOOK_URL")

SKIP_WORDS = {
    "KeyXP", "Current Giveaway", "FAQs", "About KeyXP", "My Account",
    "Log in with Discord", "Discord", "Why Discord? See our", "for more info."
}

def load_old():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_new(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def clean(text):
    return re.sub(r"\s+", " ", text).strip()

def scrape_keyxp():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    lower = text.lower()

    title = "KeyXP Giveaway"
    for line in text.split("\n"):
        line = clean(line)
        if "giveaway" in line.lower() and 5 < len(line) < 80 and line != "Current Giveaway":
            title = line
            break

    status = "Available"
    if any(x in lower for x in ["giveaway closed", "no keys", "all keys", "ended", "expired"]):
        status = "Closed"

    games = []
    for a in soup.find_all("a"):
        name = clean(a.get_text(" ", strip=True))
        href = a.get("href", "")

        if not name or name in SKIP_WORDS:
            continue

        if len(name) > 70:
            continue

        if "steam" in href.lower() or "store.steampowered" in href.lower() or name.lower() in lower:
            if name not in games:
                games.append(name)

    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src:
            full = urljoin(URL, src)
            if full not in images:
                images.append(full)

    main_image = images[0] if images else None

    return {
        "title": title,
        "status": status,
        "url": URL,
        "games": games[:10] or ["Check website for featured games"],
        "image": main_image,
    }

def send_discord(data):
    available = data["status"] == "Available"
    status_text = "🟢 Available" if available else "🔴 Closed"
    color = "FFC400" if available else "E74C3C"

    games_text = "\n".join(f"🎮 **{g}**" for g in data["games"])

    embed = DiscordEmbed(
        title="🎁 KeyXP Giveaway Updated!",
        description=(
            f"**Giveaway:** {data['title']}\n"
            f"**Status:** {status_text}\n\n"
            f"📋 **Featured Games:**\n{games_text}\n\n"
            f"🔗 **[Claim Giveaway]({data['url']})**"
        ),
        color=color,
    )

    if data.get("image"):
        embed.set_image(url=data["image"])

    embed.set_footer(text="KeyXP Giveaway Notifier • Subho")
    embed.set_timestamp()

    webhook = DiscordWebhook(
        url=WEBHOOK,
        content="🎁 **KeyXP giveaway updated!**"
    )
    webhook.add_embed(embed)
    webhook.execute()

def main():
    if not WEBHOOK:
        print("WEBHOOK_URL missing")
        return

    old = load_old()
    new = scrape_keyxp()

    if old != new:
        send_discord(new)
        save_new(new)
        print("Posted:", new)
    else:
        print("No change")

if __name__ == "__main__":
    main()
