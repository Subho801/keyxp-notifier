import os
import json
import re
import requests
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook, DiscordEmbed

URL = "https://keyxp.co/giveaway"
DATA_FILE = "keyxp_last.json"
WEBHOOK = os.getenv("WEBHOOK_URL")

KNOWN_GAMES = [
    "AWAY: Journey to the Unexpected",
    "Passing By - A Tailwind Journey",
    "Spitkiss",
    "Yono and the Celestial Elephants",
    "reky",
]

GAME_IMAGES = {
    "AWAY: Journey to the Unexpected": "https://cdn.cloudflare.steamstatic.com/steam/apps/573110/header.jpg",
    "Passing By - A Tailwind Journey": "https://cdn.cloudflare.steamstatic.com/steam/apps/2085440/header.jpg",
    "Spitkiss": "https://cdn.cloudflare.steamstatic.com/steam/apps/803600/header.jpg",
    "Yono and the Celestial Elephants": "https://cdn.cloudflare.steamstatic.com/steam/apps/602430/header.jpg",
    "reky": "https://cdn.cloudflare.steamstatic.com/steam/apps/1738860/header.jpg",
}

KEYXP_LOGO = "https://keyxp.co/favicon.ico"


def load_old():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_new(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


def scrape_keyxp():
    r = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=25,
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    lower_text = text.lower()

    title = "KeyXP Giveaway"

    for line in text.split("\n"):
        line = clean_text(line)
        if "giveaway" in line.lower() and len(line) <= 80:
            if line.lower() not in ["current giveaway"]:
                title = line
                break

    status = "Available"
    if any(x in lower_text for x in ["giveaway closed", "all keys", "no keys", "ended", "expired"]):
        status = "Closed"

    games = []
    for game in KNOWN_GAMES:
        if game.lower() in lower_text:
            games.append(game)

    if not games:
        games = KNOWN_GAMES

    image = GAME_IMAGES.get(games[0], KEYXP_LOGO)

    return {
        "title": title,
        "status": status,
        "url": URL,
        "games": games,
        "image": image,
    }


def send_discord(data):
    is_available = data["status"] == "Available"

    status_text = "🟢 Available" if is_available else "🔴 Closed"
    color = "FFC400" if is_available else "E74C3C"

    games_text = "\n".join([f"🎮 **{game}**" for game in data["games"]])

    description = (
        f"🎁 **{data['title']}**\n\n"
        f"**Status:** {status_text}\n\n"
        f"📋 **Featured Games:**\n"
        f"{games_text}\n\n"
        f"🔗 **[Claim Giveaway]({data['url']})**"
    )

    embed = DiscordEmbed(
        title="🎁 KeyXP Giveaway Updated!",
        description=description,
        color=color,
    )

    embed.set_thumbnail(url=KEYXP_LOGO)
    embed.set_image(url=data["image"])
    embed.set_footer(text="KeyXP Giveaway Notifier • Subho")
    embed.set_timestamp()

    webhook = DiscordWebhook(
        url=WEBHOOK,
        content="🎁 **New KeyXP giveaway update found!**"
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
