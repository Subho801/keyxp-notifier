import os
import json
import requests
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook, DiscordEmbed

URL = "https://keyxp.co/giveaway"
DATA_FILE = "keyxp_last.json"
WEBHOOK = os.getenv("WEBHOOK_URL")

def load_old():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_new(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def scrape_keyxp():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    status = "Available"
    if "giveaway closed" in text.lower() or "no keys" in text.lower():
        status = "Closed"

    lines = text.split("\n")

    title = "KeyXP Giveaway"
    games = []

    for line in lines:
        clean = line.strip()
        if "giveaway" in clean.lower() and len(clean) < 80:
            title = clean
        if clean and len(clean) < 60:
            if clean not in games and any(word in text for word in [clean]):
                if clean not in ["Current Giveaway", "FAQs", "About KeyXP", "My Account"]:
                    games.append(clean)

    return {
        "title": title,
        "status": status,
        "url": URL,
        "games": games[:8]
    }

def send_discord(data):
    games_text = "\n".join([f"• {g}" for g in data["games"]]) or "Check website"

    embed = DiscordEmbed(
        title=data["title"],
        description=f"**Status:** {data['status']}\n\n**Games:**\n{games_text}\n\n[Open Giveaway]({data['url']})",
        color="ffc400" if data["status"] == "Available" else "ff3333"
    )

    embed.set_footer(text="KeyXP Giveaway Notifier")

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
