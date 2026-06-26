import os
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from discord_webhook import DiscordWebhook, DiscordEmbed
from playwright.sync_api import sync_playwright

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


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def get_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
        )

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_selector(".giveaway-hero-title", timeout=30000)
        except Exception:
            print("Could not find giveaway selector. Saving debug.html")

        html = page.content()

        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)

        browser.close()
        return html


def scrape_keyxp():
    html = get_html()
    soup = BeautifulSoup(html, "html.parser")

    print("TITLE:", soup.select_one(".giveaway-hero-title"))
    print("GAME LINKS:", len(soup.select(".giveaway-hero-game-link")))
    print("IMAGES:", len(soup.select(".giveaway-hero-card-image img")))

    page_text = soup.get_text(" ", strip=True).lower()

    title_el = soup.select_one(".giveaway-hero-title")
    title = clean(title_el.get_text()) if title_el else "KeyXP Giveaway"

    stats = []
    for span in soup.select(".giveaway-hero-stats span"):
        value = clean(span.get_text())
        if value and value != "|":
            stats.append(value)

    status = "Available"
    if any(x in page_text for x in ["giveaway closed", "no keys", "all keys gone", "ended", "expired"]):
        status = "Closed"

    games = []
    for link in soup.select(".giveaway-hero-games-list .giveaway-hero-game-link"):
        name_el = link.select_one("span")
        name = clean(name_el.get_text()) if name_el else clean(link.get_text())
        href = link.get("href")

        if name:
            games.append({
                "name": name,
                "url": href,
            })

    images = {}
    for img in soup.select(".giveaway-hero-card-image img"):
        name = clean(img.get("alt", ""))
        src = img.get("src")

        if name and src:
            images[name] = urljoin(URL, src)

    for game in games:
        game["image"] = images.get(game["name"])

    banner_image = next((g.get("image") for g in games if g.get("image")), None)

    description_el = soup.select_one(".giveaway-hero-description")
    description = clean(description_el.get_text()) if description_el else ""

    end_notice_el = soup.select_one(".giveaway-hero-end-notice")
    end_notice = clean(end_notice_el.get_text()) if end_notice_el else ""

    return {
        "title": title,
        "status": status,
        "url": URL,
        "stats": stats,
        "description": description,
        "end_notice": end_notice,
        "games": games,
        "banner_image": banner_image,
    }


def send_discord(data):
    available = data["status"] == "Available"
    status_text = "🟢 Available" if available else "🔴 Closed"
    color = "FFC400" if available else "E74C3C"

    stats_text = " | ".join(data.get("stats", [])) or "Steam keys giveaway"

    games_lines = []
    for game in data["games"]:
        name = game["name"]
        url = game.get("url")

        if url:
            games_lines.append(f"🎮 [{name}]({url})")
        else:
            games_lines.append(f"🎮 **{name}**")

    games_text = "\n".join(games_lines) or "Check website for featured games"

    embed = DiscordEmbed(
        title=f"🎁 {data['title']}",
        description=(
            f"**Status:** {status_text}\n"
            f"**Info:** {stats_text}\n\n"
            f"📋 **Featured Games:**\n"
            f"{games_text}\n\n"
            f"🔗 **[Claim Giveaway]({data['url']})**"
        ),
        color=color,
    )

    if data.get("description"):
        embed.add_embed_field(
            name="📝 Details",
            value=data["description"][:1024],
            inline=False,
        )

    if data.get("end_notice"):
        embed.add_embed_field(
            name="⚠️ Notice",
            value=data["end_notice"][:1024],
            inline=False,
        )

    if data.get("banner_image"):
        embed.set_image(url=data["banner_image"])

    embed.set_footer(text="KeyXP Giveaway Notifier • Subho")
    embed.set_timestamp()

    webhook = DiscordWebhook(
        url=WEBHOOK,
        content="🎁 **KeyXP giveaway updated!**",
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
        print("Posted:", json.dumps(new, indent=2))
    else:
        print("No change")


if __name__ == "__main__":
    main()
