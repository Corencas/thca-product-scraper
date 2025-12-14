import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.settings import get_database_url

import os
import time
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
import re
import imaplib
import email
import uuid

import requests
from bs4 import BeautifulSoup
from db_sync import sync_seen_to_db

KACHE_LEAFLY_MENU_API_URL = "https://consumer-api.leafly.com/api/dispensaries/v2/kache-thca/menu_items?take=30&skip=0&&filter[medical]=false"

# ==========================================
# SECRETS / TOKENS / WEBHOOKS
# ==========================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# Webhooks for each product type (Discord channels)
WEBHOOKS = {
    "live_resin": os.getenv("DISCORD_WEBHOOK_LIVE_RESIN", ""),
    "rosin": os.getenv("DISCORD_WEBHOOK_ROSIN", ""),
    "flower": os.getenv("DISCORD_WEBHOOK_FLOWER", ""),
    "price_tracker": os.getenv("DISCORD_WEBHOOK_PRICE_TRACKER", ""),
    "drop_calendar": os.getenv("DISCORD_WEBHOOK_DROP_CALENDAR", ""),
}

# Webhook for price & inventory tracker channel (#price-tracker)
PRICE_TRACKER_WEBHOOK = "https://discord.com/api/webhooks/1447800750355779868/xGv9v48qwAdGCC9TC0lgSOWY6qset1XV_RbXoYq9t7p_oVxHeIsp2nhJhAnDBH5xpsvz"

# Simple patterns for extracting prices & stock text
PRICE_REGEX = re.compile(r"\$([0-9]+(?:\.[0-9]{1,2})?)")
STOCK_OUT_KEYWORDS = ("sold out", "out of stock", "coming soon")

# New: a dedicated webhook for the drop calendar / reminders channel
DROP_CALENDAR_WEBHOOK = "https://discord.com/api/webhooks/1447682471327039548/DsS4kiKcJc_QKAl-AG-bQJraPuHbN9kWyLtlrYuLSf7BEhC7c4eS-3__LlcCOPBpvnur"

# Optional fallback if classification fails (can leave as None)
DEFAULT_WEBHOOK = os.getenv("DEFAULT_DISCORD_WEBHOOK", "").strip() or None

# How often to check all pages (seconds)
CHECK_INTERVAL_SECONDS = 4

# How often to poll email for new drop announcements (seconds)
EMAIL_CHECK_INTERVAL_SECONDS = 30

# File to remember which products we’ve already seen
SEEN_FILE = Path("seen_products.json")

# File to remember scheduled drop events (email + manual)
DROP_EVENTS_FILE = Path("scheduled_drops.json")

# Pages to watch (can mix all product types on the same page)
SITES = [
    # Tesoro – Shop Products and Wholesale
    {
        "name": "Tesoro - Shop Products",
        "url": "https://tesorohemp.com/collections/shop-products",
        "parser": "parse_tesoro_shop",
    },
    {
        "name": "Tesoro - Shop Wholesale",
        "url": "https://tesorohemp.com/collections/shop-wholesale",
        "parser": "parse_tesoro_shop",
    },
    # StoneyBranch – THCA Flower
    {
        "name": "StoneyBranch Flower THCA",
        "url": "https://stoneybranch.com/collections/flower",
        "parser": "parse_stoneybranch",
    },
    # Hello Mary – THCA Flower (8 pages)
    {
        "name": "Hello Mary - Flower p1",
        "url": "https://shophellomary.com/category/flower/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p2",
        "url": "https://shophellomary.com/category/flower/page/2/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p3",
        "url": "https://shophellomary.com/category/flower/page/3/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p4",
        "url": "https://shophellomary.com/category/flower/page/4/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p5",
        "url": "https://shophellomary.com/category/flower/page/5/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p6",
        "url": "https://shophellomary.com/category/flower/page/6/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p7",
        "url": "https://shophellomary.com/category/flower/page/7/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Flower p8",
        "url": "https://shophellomary.com/category/flower/page/8/",
        "parser": "parse_hellomary",
    },
    # Hello Mary – Rosin
    {
        "name": "Hello Mary - Rosin p1",
        "url": "https://shophellomary.com/category/concentrates/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Rosin p2",
        "url": "https://shophellomary.com/category/concentrates/page/2/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Rosin p3",
        "url": "https://shophellomary.com/category/concentrates/page/3/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Rosin p4",
        "url": "https://shophellomary.com/category/concentrates/page/4/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Rosin p5",
        "url": "https://shophellomary.com/category/concentrates/page/5/",
        "parser": "parse_hellomary",
    },
    {
        "name": "Hello Mary - Rosin p6",
        "url": "https://shophellomary.com/category/concentrates/page/6/",
        "parser": "parse_hellomary",
    },
    # Kache THCa – Leafly Menu
    {
        "name": "Kache THCa - Leafly Menu",
        "url": "https://kachethca.com/",
        "parser": "parse_kache_leafly",
    },
]

# Keyword-based classification rules (you can tweak these)
CLASSIFICATION_KEYWORDS = {
    "live_resin": [
        "live resin",
        "live-resin",
        "liveresin",
        "lr thca",
    ],
    "rosin": [
        "rosin",
        "hash rosin",
        "live rosin",
    ],
    "flower": [
        "flower",
        "bud",
        "buds",
        "smalls",
        "thca flower",
        "tier",
        "exotic",
    ],
}

# ==========================================
# EMAIL CONFIG (FILL THIS FOR DROP EMAILS)
# ==========================================

EMAIL_CONFIG = {
    "enabled": False,          # set to True after you fill host/user/password
    "host": "imap.gmail.com",  # e.g. Gmail IMAP host
    "username": "your_email@example.com",
    "password": "your_email_app_password",
    "folder": "INBOX",
}

# ==========================================
# DROP REMINDER SETTINGS
# ==========================================

# Reminder offsets before drop time

# 4 days, 6 hours, and at drop(0)
DROP_REMINDER_OFFSETS_SECONDS = [
    4 * 24 * 60 * 60,   # 4 days
    6 * 60 * 60,        # 6 hours
    0,                  # drop time
]

# -----------------
# URL NORMALIZATION HELPER
# -----------------
def normalize_product_url(base_url: str, href: str) -> str:
    """
    Turn a relative/absolute href into a canonical product URL:
    - join with base_url
    - strip query params and fragments
    - strip trailing slash
    """
    full = urljoin(base_url, href)
    parts = urlsplit(full)
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))

# =========================
# DISCORD
# =========================

TYPE_EMOJIS = {
    "live_resin": "🧪",
    "rosin": "🧈",
    "flower": "🌿",
}

EMBED_COLORS = {
    "live_resin": 0xF97316,  # orange
    "rosin": 0xFACC15,       # yellow
    "flower": 0x22C55E,      # green
}

# Optional vendor-specific branding (fill logo URLs with your real ones)
VENDOR_BRANDING = {
    "Tesoro": {
        "display_name": "Tesoro Hemp",
        "logo_url": "https://example.com/tesoro-logo.png",
        "color": 0x10B981,
    },
    "Hello Mary": {
        "display_name": "Hello Mary",
        "logo_url": "https://example.com/hellomary-logo.png",
        "color": 0xEC4899,
    },
    "StoneyBranch": {
        "display_name": "StoneyBranch",
        "logo_url": "https://example.com/stoneybranch-logo.png",
        "color": 0xF59E0B,
    },
    "Kache THCa": {
        "display_name": "Kache THCa",
        "logo_url": "https://example.com/kache-logo.png",
        "color": 0x3B82F6,
    },
}


def apply_vendor_branding(embed: dict, site_name: str) -> dict:
    """
    Apply vendor-specific logo/color branding to an embed based on the site name.
    """
    site_lower = site_name.lower()

    for key, cfg in VENDOR_BRANDING.items():
        if key.lower() in site_lower:
            # Color: only override if embed doesn't already have one
            if "color" in cfg and "color" not in embed:
                embed["color"] = cfg["color"]

            logo = cfg.get("logo_url")
            if logo:
                author = embed.get("author") or {}
                if "name" not in author:
                    author["name"] = cfg.get("display_name", key)
                author["icon_url"] = logo
                embed["author"] = author

            break

    return embed


def send_discord_message(message: str, product_type: str, embed: dict | None = None) -> None:
    """Send a message (and optional embed) to the Discord channel for the given product_type."""
    webhook_url = WEBHOOKS.get(product_type) or DEFAULT_WEBHOOK

    if not webhook_url:
        print(f"[WARN] No webhook configured for type '{product_type}', skipping.")
        return

    payload: dict = {"content": message}
    if embed is not None:
        payload["embeds"] = [embed]

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to send Discord message for type '{product_type}': {e}")


def send_calendar_message(message: str, embed: dict | None = None) -> None:
    """
    Send a message to the dedicated drop calendar / reminder channel.
    """
    if not DROP_CALENDAR_WEBHOOK:
        print("[WARN] DROP_CALENDAR_WEBHOOK not set; skipping calendar message.")
        return

    payload: dict = {"content": message}
    if embed is not None:
        payload["embeds"] = [embed]

    try:
        resp = requests.post(
            DROP_CALENDAR_WEBHOOK,
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to send calendar message: {e}")


def send_price_tracker_message(message: str, embed: dict | None = None) -> None:
    """
    Send a message to the dedicated #price-tracker channel
    for price and inventory changes.
    """
    if not PRICE_TRACKER_WEBHOOK:
        print("[WARN] PRICE_TRACKER_WEBHOOK not set; skipping price tracker message.")
        return

    payload: dict = {"content": message}
    if embed is not None:
        payload["embeds"] = [embed]

    try:
        resp = requests.post(
            PRICE_TRACKER_WEBHOOK,
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to send price tracker message: {e}")


# =========================
# SEEN PRODUCT CACHE
# =========================

def load_seen():
    """
    seen is a dict keyed by product_id so one product appearing on multiple
    pages only notifies once:
    {
        "https://.../products/foo": {
            "first_seen": "...",
            "title": "...",
        },
        ...
    }
    """
    if SEEN_FILE.exists():
        try:
            with SEEN_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not read seen file, starting fresh: {e}")
            return {}
    return {}


def save_seen(seen):
    try:
        with SEEN_FILE.open("w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save seen file: {e}")


# =========================
# DROP EVENTS PERSISTENCE
# =========================

def load_drop_events():
    """
    Load scheduled drop events from disk, if any.
    Format:
    [
        {
            "id": "...",
            "name": "...",
            "url": "...",
            "drop_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
            "source": "email" or "manual",
            "reminders_sent": [seconds, ...]
        },
        ...
    ]
    """
    if DROP_EVENTS_FILE.exists():
        try:
            with DROP_EVENTS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"[WARN] Could not read drop events file, starting fresh: {e}")
    return []


def save_drop_events(events):
    try:
        with DROP_EVENTS_FILE.open("w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save drop events: {e}")


def parse_iso_utc(dt_str: str) -> datetime:
    """
    Parse a UTC ISO string like 'YYYY-MM-DDTHH:MM:SSZ' or 'YYYY-MM-DD HH:MM:SS'.
    """
    dt_str = dt_str.strip()
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1]
    # allow both 'T' and space
    dt_str = dt_str.replace("T", " ")
    # try with seconds
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Could not parse datetime string: {dt_str}")


def format_iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# =========================
# HTTP + PARSERS
# =========================

def fetch_html(url: str) -> str:
    headers = {
        # Pretend to be a normal browser so Shopify / Cloudflare are happy
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def fetch_og_image(url: str) -> str | None:
    """
    Try to fetch the Open Graph image (og:image) for a given product URL.
    This usually gives a nice product/hero image for WordPress / Shopify sites.
    """
    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        tag = soup.find("meta", property="og:image")
        if tag and tag.get("content"):
            return tag["content"].strip() or None

        # Fallback: some themes use name="og:image"
        tag = soup.find("meta", attrs={"name": "og:image"})
        if tag and tag.get("content"):
            return tag["content"].strip() or None

    except Exception as e:
        print(f"[WARN] Failed to fetch og:image for {url}: {e}")

    return None


def fetch_potency_and_flavor(url: str) -> dict:
    """
    Fetch product page and try to extract:
    - THCA %
    - Total cannabinoids %
    - CBD %
    - Flavor / aroma / taste descriptors

    Returns:
    {
        "thca_percent": float | None,
        "total_cannabinoids_percent": float | None,
        "cbd_percent": float | None,
        "flavor_text": str,
    }
    """
    result = {
        "thca_percent": None,
        "total_cannabinoids_percent": None,
        "cbd_percent": None,
        "flavor_text": "",
    }

    try:
        html = fetch_html(url)
    except Exception as e:
        print(f"[WARN] Failed to fetch potency/flavor info for {url}: {e}")
        return result

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    # THCA %
    m_thca = re.search(r"THCA?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, re.IGNORECASE)
    if m_thca:
        try:
            result["thca_percent"] = float(m_thca.group(1))
        except ValueError:
            pass

    # Total cannabinoids %
    m_total = re.search(r"Total\s+Cannabinoids?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, re.IGNORECASE)
    if m_total:
        try:
            result["total_cannabinoids_percent"] = float(m_total.group(1))
        except ValueError:
            pass

    # CBD %
    m_cbd = re.search(r"CBD\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, re.IGNORECASE)
    if m_cbd:
        try:
            result["cbd_percent"] = float(m_cbd.group(1))
        except ValueError:
            pass

    # Flavor / aroma / taste / smell / nose
    m_flavor = re.search(
        r"(?:Flavor|Flavour|Taste|Aroma|Smell|Nose)\s*[:\-]\s*(.+)",
        text,
        re.IGNORECASE,
    )
    if m_flavor:
        flavor = m_flavor.group(1).strip()
        # Trim to something reasonable
        if len(flavor) > 200:
            flavor = flavor[:197] + "..."
        result["flavor_text"] = flavor

    return result


def normalize_title_for_match(title: str) -> str:
    """
    Normalize product title for duplicate / restock detection.
    """
    t = title.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def find_restock_match(seen: dict, site_name: str, normalized_title: str, image_url: str | None) -> str | None:
    """
    Look through previously seen products from the same site and try
    to find a product with the same normalized title or image URL.
    Returns the product_id of the match if found.
    """
    for pid, info in seen.items():
        if info.get("site") != site_name:
            continue

        prev_norm = info.get("normalized_title")
        if prev_norm and prev_norm == normalized_title:
            return pid

        if image_url and info.get("image_url") and image_url == info.get("image_url"):
            return pid

    return None


def handle_price_and_stock_changes(
    product: dict,
    seen_entry: dict,
    site_name: str,
    now_str: str,
):
    """
    Compare current price / stock with the last known values and send
    messages to the #price-tracker channel if something changed.
    """
    title = product["title"]
    url = product["url"]

    new_price = product.get("price")
    new_in_stock = product.get("in_stock")

    old_price = seen_entry.get("last_price")
    old_in_stock = seen_entry.get("last_in_stock")

    # Price change
    if new_price is not None and old_price is not None and new_price != old_price:
        diff = new_price - old_price
        direction = "decreased" if diff < 0 else "increased"
        emoji = "�" if diff < 0 else "�"

        pct_change = 0.0
        if old_price:
            pct_change = abs(diff) / old_price * 100.0

        msg_lines = [
            f"{emoji} **Price {direction}!**",
            f"**Site:** {site_name}",
            f"**Product:** [{title}]({url})",
            f"**Old price:** ${old_price:.2f}",
            f"**New price:** ${new_price:.2f}",
            f"**Change:** {'+' if diff > 0 else '-'}${abs(diff):.2f} ({pct_change:.1f}%)",
            f"**Detected (UTC):** {now_str}",
        ]
        msg = "\n".join(msg_lines)

        embed: dict = {
            "title": title,
            "url": url,
            "description": f"Price {direction} at {site_name}",
            "fields": [
                {"name": "Old price", "value": f"${old_price:.2f}", "inline": True},
                {"name": "New price", "value": f"${new_price:.2f}", "inline": True},
            ],
            "footer": {"text": f"Detected at {now_str} UTC"},
        }

        image_url = product.get("image_url") or seen_entry.get("image_url") or fetch_og_image(url)
        if image_url:
            embed["thumbnail"] = {"url": image_url}

        embed = apply_vendor_branding(embed, site_name)
        send_price_tracker_message(msg, embed)

        # Inventory / stock change
    if new_in_stock is not None and old_in_stock is not None and new_in_stock != old_in_stock:
        # Only notify when going OUT of stock.
        # We intentionally skip "Back in stock" messages because
        # the product drop announcement already covers that.
        if new_in_stock:
            # Went from False -> True (restock): do nothing
            return

        # Went from True -> False (sold out)
        status_text = "Went out of stock"
        emoji = "⚠️"

        msg_lines = [
            f"{emoji} **Inventory update**",
            f"**Site:** {site_name}",
            f"**Product:** [{title}]({url})",
            f"**Status:** {status_text}",
            f"**Detected (UTC):** {now_str}",
        ]
        msg = "\n".join(msg_lines)

        embed: dict = {
            "title": title,
            "url": url,
            "description": status_text,
            # NOTE: No potency / flavor here per your request
            "footer": {"text": f"Detected at {now_str} UTC"},
        }

        image_url = product.get("image_url") or seen_entry.get("image_url") or fetch_og_image(url)
        if image_url:
            embed["thumbnail"] = {"url": image_url}

        embed = apply_vendor_branding(embed, site_name)
        send_price_tracker_message(msg, embed)


def parse_tesoro_shop(site_config):
    """
    Parse a Tesoro collection page and return a list of product dicts:
    {
        "id": unique_id_for_product,
        "title": product_title,
        "url": product_url,
    }
    """
    html = fetch_html(site_config["url"])
    if html is None:
        # In case the request failed for some reason
        print(f"[ERROR] Could not fetch HTML for {site_config['url']}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    products = []
    seen_urls = set()

    # Grab all links that go to /products/...
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/products/" not in href:
            continue

        full_url = normalize_product_url(site_config["url"], href)

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        raw_title = a.get_text(" ", strip=True)
        if not raw_title:
            continue

        # Price
        price = None
        m_price = PRICE_REGEX.search(raw_title)
        if m_price:
            try:
                price = float(m_price.group(1))
            except ValueError:
                price = None

        # Stock: assume sold out if those keywords appear, else in stock
        lower = raw_title.lower()
        in_stock = True
        for kw in STOCK_OUT_KEYWORDS:
            if kw in lower:
                in_stock = False
                break

        # Clean title (you can keep price in it if you prefer)
        title = raw_title

        products.append(
            {
                "id": full_url,
                "title": title,
                "url": full_url,
                "price": price,
                "in_stock": in_stock,
            }
        )

    return products


def parse_hellomary(site_config) -> list[dict]:
    """
    Parse a Hello Mary category page and return a list of product dicts.
    Works for URLs like:
      - https://shophellomary.com/category/flower/
      - https://shophellomary.com/category/concentrates/
      - .../page/2/, /page/3/, etc.
    """
    html = fetch_html(site_config["url"])
    if html is None:
        print(f"[ERROR] Could not fetch HTML for {site_config['url']}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    products: list[dict] = []
    seen_urls: set[str] = set()

    # On the category page, each product entry is a link that goes to /shop/...
    for a in soup.select("a[href*='/shop/']"):
        href = (a.get("href") or "").strip()
        if not href:
            continue

        raw_title = a.get_text(" ", strip=True)
        if not raw_title:
            continue

        # Require a price marker to treat this as a product tile
        if "$" not in raw_title:
            continue

        full_url = normalize_product_url(site_config["url"], href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Price
        price = None
        m_price = PRICE_REGEX.search(raw_title)
        if m_price:
            try:
                price = float(m_price.group(1))
            except ValueError:
                price = None

        # Stock
        lower = raw_title.lower()
        in_stock = True
        for kw in STOCK_OUT_KEYWORDS:
            if kw in lower:
                in_stock = False
                break

        title = raw_title

        products.append(
            {
                "id": full_url,
                "title": title,
                "url": full_url,
                "price": price,
                "in_stock": in_stock,
            }
        )

    return products


def parse_stoneybranch(site_config) -> list[dict]:
    """
    Parse a Stoney Branch collection page and return a list of product dicts:
    {
        "id": unique_id_for_product,
        "title": product_title,
        "url": product_url,
        "price": float | None,
        "in_stock": bool | None,
    }
    """
    html = fetch_html(site_config["url"])
    if html is None:
        print(f"[ERROR] Could not fetch HTML for {site_config['url']}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    products: list[dict] = []
    seen_urls: set[str] = set()

    for a in soup.select("a[href*='/products/']"):
        href = (a.get("href") or "").strip()
        if not href:
            continue

        raw_title = a.get_text(" ", strip=True)
        if not raw_title or raw_title.lower() in {"quick view", "view"}:
            continue

        full_url = normalize_product_url(site_config["url"], href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Price
        price = None
        m_price = PRICE_REGEX.search(raw_title)
        if m_price:
            try:
                price = float(m_price.group(1))
            except ValueError:
                price = None

        # Stock
        lower = raw_title.lower()
        in_stock = True
        for kw in STOCK_OUT_KEYWORDS:
            if kw in lower:
                in_stock = False
                break

        title = raw_title

        products.append(
            {
                "id": full_url,   # use canonical URL as ID
                "title": title,
                "url": full_url,
                "price": price,
                "in_stock": in_stock,
            }
        )

    print(f"[DEBUG] StoneyBranch parser found {len(products)} products on {site_config['url']}")
    return products


def find_first_image_url_in_obj(obj) -> str | None:
    """
    Recursively search a dict/list structure for the first string
    that looks like an image URL (ending in .jpg/.jpeg/.png/.webp/.gif).
    """
    if isinstance(obj, str):
        s = obj.strip()
        if re.match(r"^https?://.*\.(?:jpg|jpeg|png|webp|gif)$", s, re.IGNORECASE):
            return s
        return None

    if isinstance(obj, dict):
        for v in obj.values():
            url = find_first_image_url_in_obj(v)
            if url:
                return url
        return None

    if isinstance(obj, list):
        for v in obj:
            url = find_first_image_url_in_obj(v)
            if url:
                return url
        return None

    return None


def parse_kache_leafly(site_config):
    """
    Parse Kache THCa's Leafly JSON into your product watcher format:
    {
        "id": <id>, "title": <title>, "url": <menu_page_url>, "image_url": <optional>
    }
    """
    data = fetch_kache_leafly_menu()

    items = data.get("data", [])

    products: list[dict] = []
    for item in items:
        product_id = str(item.get("id"))

        title = (
            item.get("name")
            or item.get("brandName")
            or f"Product {product_id}"
        )

        image_url = None

        # 1) Existing logic: look in "image" object if present
        image_obj = item.get("image")
        if isinstance(image_obj, dict):
            image_url = (
                image_obj.get("url")
                or image_obj.get("fullSizeUrl")
                or image_obj.get("imageUrl")
                or image_obj.get("src")
            )

        # 2) Look in "photos" / "images" arrays
        if not image_url:
            photos = item.get("photos") or item.get("images") or []
            if isinstance(photos, list) and photos:
                first = photos[0] or {}
                if isinstance(first, dict):
                    image_url = (
                        first.get("url")
                        or first.get("fullSizeUrl")
                        or first.get("thumbnailUrl")
                        or first.get("imageUrl")
                        or first.get("src")
                    )
                elif isinstance(first, str):
                    # sometimes it's just a string URL
                    image_url = first.strip()

        # 3) Generic fallback: scan the whole item for any image-like URL
        if not image_url:
            image_url = find_first_image_url_in_obj(item)

        if not image_url:
            print(f"[DEBUG] No image URL found for Leafly item {product_id} ({title})")
        else:
            print(f"[DEBUG] Image URL for {title}: {image_url}")

        products.append(
            {
                "id": product_id,
                "title": title,
                "url": site_config["url"],
                "image_url": image_url,
                "price": None,
                "in_stock": None,
            }
        )

    print(f"[DEBUG] Kache Leafly parser found {len(products)} products")
    return products


def fetch_kache_leafly_menu():
    headers = {
        "User-Agent": "ProductDropWatcher/1.0",
        "Accept": "application/json",
        "Referer": "https://kachethca.com/",
    }

    try:
        resp = requests.get(KACHE_LEAFLY_MENU_API_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch Kache Leafly menu: {e}")
        # Return an empty structure so parse_kache_leafly can handle it gracefully
        return {"data": []}


PARSERS = {
    "parse_tesoro_shop": parse_tesoro_shop,
    "parse_stoneybranch": parse_stoneybranch,
    "parse_hellomary": parse_hellomary,
    "parse_kache_leafly": parse_kache_leafly,
}


# =========================
# CLASSIFICATION
# =========================

def classify_product(title: str) -> str | None:
    """
    Return 'live_resin', 'rosin', 'flower', or None if we can't tell.
    Uses simple keyword matching on the product title.
    """
    lower_title = title.lower()

    for ptype, keywords in CLASSIFICATION_KEYWORDS.items():
        for kw in keywords:
            if kw in lower_title:
                return ptype

    return None


# =========================
# DROP SCHEDULER / REMINDERS
# =========================


def schedule_drop_event(
    events: list,
    name: str,
    url: str | None,
    drop_time_utc: datetime,
    source: str,
    event_id: str | None = None,
    image_url: str | None = None,
    logo_url: str | None = None,
):
    """
    Create a new drop event and append it to the events list.
    image_url = product image if available
    logo_url  = vendor logo if product image not available
    """
    if event_id is None:
        event_id = f"{source}-{uuid.uuid4()}"

    event = {
        "id": event_id,
        "name": name,
        "url": url or "",
        "drop_time_utc": format_iso_utc(drop_time_utc),
        "source": source,
        "reminders_sent": [],
        "image_url": image_url or "",
        "logo_url": logo_url or "",
    }
    events.append(event)

    # Discord timestamp formatting
    unix_ts = int(drop_time_utc.timestamp())
    discord_time_full = f"<t:{unix_ts}:f>"      # e.g. December 9, 2025 at 1:00 AM
    discord_time_relative = f"<t:{unix_ts}:R>"  # e.g. in 4 days

    url_part = f"\n🔗 {url}" if url else ""
    msg = (
        f"📅 **New drop scheduled ({source})**\n"
        f"**Product:** {name}\n"
        f"**Drop Time:** {discord_time_full} ({discord_time_relative}){url_part}"
    )

    # Choose an image: prefer product image, fall back to logo
    hero_image = (image_url or "") or (logo_url or "")

    embed: dict = {
        "title": name,
        "url": url or None,
        "description": f"Drop scheduled via {source}",
        "footer": {"text": f"Drop Time (UTC): {format_iso_utc(drop_time_utc)}"},
    }
    if hero_image:
        embed["image"] = {"url": hero_image}

    send_calendar_message(msg, embed)
    print(f"[DROP] Scheduled drop event {event_id} ({name}) at {format_iso_utc(drop_time_utc)}")
    return events


def check_drop_reminders(events: list):
    """
    Check all scheduled events and send reminders at configured offsets.
    Uses Discord timestamps and includes product/brand image if available.
    Also prunes events a couple of days after drop once all reminders are sent.
    """
    if not events:
        return events

    now = datetime.now(timezone.utc)

    for event in events:
        drop_time = parse_iso_utc(event["drop_time_utc"])
        seconds_to_drop = (drop_time - now).total_seconds()
        already_sent = set(event.get("reminders_sent") or [])

        image_url = event.get("image_url") or ""
        logo_url = event.get("logo_url") or ""
        hero_image = image_url or logo_url
        url = event.get("url") or ""
        name = event["name"]

        for offset in DROP_REMINDER_OFFSETS_SECONDS:
            if offset in already_sent:
                continue

            # Fire when we cross the offset window
            if seconds_to_drop <= offset and seconds_to_drop > offset - CHECK_INTERVAL_SECONDS * 2:
                event["reminders_sent"].append(offset)

                url_part = f"\n🔗 {url}" if url else ""

                # Discord timestamps
                unix_ts = int(drop_time.timestamp())
                discord_time_full = f"<t:{unix_ts}:f>"
                discord_time_relative = f"<t:{unix_ts}:R>"

                if offset > 0:
                    msg = (
                        f"⏰ **Upcoming drop:** {name}\n"
                        f"Drop at {discord_time_full} ({discord_time_relative}){url_part}"
                    )
                else:
                    msg = (
                        f"🚀 **Drop time now!** {name}\n"
                        f"Drop at {discord_time_full} ({discord_time_relative}){url_part}"
                    )

                embed = {
                    "title": name,
                    "url": url or None,
                    "description": "Drop reminder",
                    "footer": {"text": f"Drop Time (UTC): {format_iso_utc(drop_time)}"},
                }
                if hero_image:
                    embed["image"] = {"url": hero_image}

                send_calendar_message(msg, embed)
                print(f"[DROP] Sent reminder ({offset}s before) for event {event['id']}")

    # Prune old events: >2 days after drop and all reminders sent
    cutoff_seconds = 2 * 24 * 60 * 60
    filtered: list[dict] = []
    for event in events:
        drop_time = parse_iso_utc(event["drop_time_utc"])
        seconds_since_drop = (now - drop_time).total_seconds()
        all_offsets = set(DROP_REMINDER_OFFSETS_SECONDS)
        sent = set(event.get("reminders_sent") or [])

        if seconds_since_drop > cutoff_seconds and sent >= all_offsets:
            print(f"[DROP] Pruning old event {event['id']} ({event['name']})")
            continue

        filtered.append(event)

    return filtered


def prompt_manual_drops(events: list):
    """
    Prompt user to manually add drops at startup.
    Times should be entered in UTC in format: YYYY-MM-DD HH:MM
    Now supports optional product image + vendor logo URLs.
    """
    print("\n=== Manual Drop Entry (optional) ===")
    print("Press Enter on product name to skip/finish.")

    while True:
        name = input("Product name (or Enter to finish): ").strip()
        if not name:
            break

        url = input("Product URL (optional): ").strip()
        dt_str = input("Drop time in UTC (YYYY-MM-DD HH:MM): ").strip()
        image_url = input("Product image URL (optional): ").strip()
        logo_url = input("Vendor logo URL (optional): ").strip()

        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            print("  !! Could not parse date/time. Please use YYYY-MM-DD HH:MM (UTC). Skipping this entry.")
            continue

        events = schedule_drop_event(
            events,
            name=name,
            url=url,
            drop_time_utc=dt,
            source="manual",
            image_url=image_url or None,
            logo_url=logo_url or None,
        )

    return events

# =========================
# EMAIL WATCHER
# =========================

def get_email_body_text(msg: email.message.Message) -> str:
    """
    Extract plain text from an email Message.
    """
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    parts.append(part.get_payload(decode=True).decode(charset, errors="replace"))
                except Exception:
                    continue
        return "\n".join(parts)
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            return msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            return ""


def parse_drop_email(subject: str, body: str):
    """
    Parser for drop announcement emails.

    Expected examples:
      Subject: DROP: Tesoro XYZ Live Rosin
      Body (anywhere):
        Drop Time (UTC): 2025-12-08 23:00
        URL: https://example.com/product/xyz
        Image: https://example.com/product-image.jpg      (optional)
        Logo:  https://example.com/vendor-logo.png        (optional)
    """
    subject = subject or ""
    body = body or ""

    # Product name from subject
    name = subject
    m = re.match(r"\s*drop\s*:\s*(.+)", subject, re.IGNORECASE)
    if m:
        name = m.group(1).strip()

    # Drop Time
    drop_time = None
    m_time = re.search(r"drop time\s*\(utc\)\s*:\s*(.+)", body, re.IGNORECASE)
    if not m_time:
        m_time = re.search(r"drop time\s*:\s*(.+)", body, re.IGNORECASE)

    if m_time:
        dt_str = m_time.group(1).strip()
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            drop_time = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                drop_time = parse_iso_utc(dt_str)
            except ValueError:
                drop_time = None

    # URL (optional)
    url = ""
    m_url = re.search(r"^url\s*:\s*(\S+)", body, re.IGNORECASE | re.MULTILINE)
    if m_url:
        url = m_url.group(1).strip()

    # Product image URL (optional)
    image_url = ""
    m_img = re.search(r"^image\s*:\s*(\S+)", body, re.IGNORECASE | re.MULTILINE)
    if m_img:
        image_url = m_img.group(1).strip()

    # Vendor logo URL (optional)
    logo_url = ""
    m_logo = re.search(r"^logo\s*:\s*(\S+)", body, re.IGNORECASE | re.MULTILINE)
    if m_logo:
        logo_url = m_logo.group(1).strip()

    if not drop_time:
        return None

    return {
        "name": name,
        "url": url,
        "drop_time_utc": drop_time,
        "image_url": image_url,
        "logo_url": logo_url,
    }


def check_email_for_drops(events: list, last_email_check_time: float) -> tuple[list, float]:
    """
    If EMAIL_CONFIG['enabled'] is True, connect to IMAP and scan for new UNSEEN emails.
    For each email that looks like a drop announcement, schedule a drop event and
    post immediately in the calendar channel.
    """
    if not EMAIL_CONFIG.get("enabled"):
        return events, last_email_check_time

    now_ts = time.time()
    if now_ts - last_email_check_time < EMAIL_CHECK_INTERVAL_SECONDS:
        return events, last_email_check_time

    last_email_check_time = now_ts

    try:
        imap = imaplib.IMAP4_SSL(EMAIL_CONFIG["host"])
        imap.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
        imap.select(EMAIL_CONFIG["folder"])
    except Exception as e:
        print(f"[ERROR] Failed to connect to IMAP: {e}")
        return events, last_email_check_time

    try:
        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK":
            print("[WARN] IMAP search for UNSEEN failed.")
            imap.logout()
            return events, last_email_check_time

        ids = data[0].split()
        if not ids:
            imap.logout()
            return events, last_email_check_time

        print(f"[EMAIL] Found {len(ids)} unseen email(s) to inspect for drops.")

        for msg_id in ids:
            typ, msg_data = imap.fetch(msg_id, "(RFC822)")
            if typ != "OK":
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = msg.get("Subject", "")
            body = get_email_body_text(msg)

            parsed = parse_drop_email(subject, body)
            if parsed:
                name = parsed["name"]
                url = parsed["url"]
                drop_time_utc = parsed["drop_time_utc"]
                image_url = parsed.get("image_url") or ""
                logo_url = parsed.get("logo_url") or ""

                event_source_id = msg.get("Message-ID") or f"email-{uuid.uuid4()}"
                event_id = f"email-{event_source_id}"

                events = schedule_drop_event(
                    events,
                    name=name,
                    url=url,
                    drop_time_utc=drop_time_utc,
                    source="email",
                    event_id=event_id,
                    image_url=image_url,
                    logo_url=logo_url,
                )
            else:
                print(f"[EMAIL] Skipped email (not recognized as drop): {subject}")

            # mark as seen
            imap.store(msg_id, "+FLAGS", "\\Seen")

        imap.logout()
    except Exception as e:
        print(f"[ERROR] IMAP processing error: {e}")

    return events, last_email_check_time


# =========================
# CORE LOGIC
# =========================

def check_site(site_config, seen):
    site_name = site_config["name"]
    parser_name = site_config["parser"]
    parser_func = PARSERS.get(parser_name)

    if parser_func is None:
        print(f"[WARN] No parser function found for {site_name} ({parser_name})")
        return seen

    try:
        products = parser_func(site_config)
    except Exception as e:
        print(f"[ERROR] Failed to parse site {site_name}: {e}")
        return seen

    if products is None:
        print(f"[WARN] Parser {parser_name} for {site_name} returned None.")
        return seen

    now_str = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    for product in products:
        product_id = product["id"]
        title = product["title"]
        url = product["url"]
        price = product.get("price")
        in_stock = product.get("in_stock")

        # Price / stock change handling for existing products
        if product_id in seen:
            seen_entry = seen[product_id]

            # Send price / inventory alerts to #price-tracker if needed
            handle_price_and_stock_changes(product, seen_entry, site_name, now_str)

            # Update stored state
            seen_entry["last_price"] = price
            seen_entry["last_in_stock"] = in_stock
            seen_entry["last_seen"] = now_str
            seen_entry["title"] = title
            seen_entry["url"] = url
            seen[product_id] = seen_entry

            continue

        # NEW product id
        # Force everything from StoneyBranch to be flower
        if "stoneybranch" in site_name.lower():
            product_type = "flower"
        else:
            product_type = classify_product(title)

        if product_type is None:
            print(f"[INFO] Unclassified product (no alert): {title} -> {url}")
            seen[product_id] = {
                "first_seen": now_str,
                "title": title,
                "url": url,
                "site": site_name,
                "product_type": product_type,
                "last_price": price,
                "last_in_stock": in_stock,
                "last_seen": now_str,
                "image_url": "",
                "normalized_title": normalize_title_for_match(title),
            }
            continue

        print(f"[NEW] {site_name} [{product_type}]: {title} -> {url}")

        pretty_type = product_type.replace("_", " ").title()
        emoji = TYPE_EMOJIS.get(product_type, "✨")

        # Image: use image_url from parser if available, else OG image
        image_url = product.get("image_url") or fetch_og_image(url)

        # Potency + flavor (only for drop posts)
        potency = fetch_potency_and_flavor(url)
        thca_percent = potency.get("thca_percent")
        total_cannabinoids = potency.get("total_cannabinoids_percent")
        cbd_percent = potency.get("cbd_percent")
        flavor_text = potency.get("flavor_text") or ""

        # Duplicate / restock detection
        normalized_title = normalize_title_for_match(title)
        restock_parent_id = find_restock_match(seen, site_name, normalized_title, image_url)

        if restock_parent_id:
            prefix = "� **Restock detected!**"
            description = f"{emoji} Restock at {site_name}"
        else:
            prefix = f"{emoji} **New {pretty_type} drop!**"
            description = f"{emoji} {pretty_type} from {site_name}"

        msg_lines = [
            prefix,
            f"**Site:** {site_name}",
            f"**Product:** [{title}]({url})",
            f"**Detected (UTC):** {now_str}",
        ]
        msg = "\n".join(msg_lines)

        embed: dict = {
            "title": title,
            "url": url,
            "description": description,
            "footer": {"text": f"Detected at {now_str} UTC"},
        }

        # Base color by type, may be overridden by vendor branding
        color = EMBED_COLORS.get(product_type)
        if color is not None:
            embed["color"] = color

        if image_url:
            embed["image"] = {"url": image_url}

        # Add potency / cannabinoid info if available
        fields: list[dict] = []

        potency_lines = []
        if thca_percent is not None:
            potency_lines.append(f"THCA: {thca_percent:.1f}%")
        if total_cannabinoids is not None:
            potency_lines.append(f"Total Cannabinoids: {total_cannabinoids:.1f}%")
        if cbd_percent is not None:
            potency_lines.append(f"CBD: {cbd_percent:.1f}%")

        if potency_lines:
            fields.append(
                {
                    "name": "Potency",
                    "value": "\n".join(potency_lines),
                    "inline": True,
                }
            )

        if flavor_text:
            fields.append(
                {
                    "name": "Flavor / Aroma / Taste",
                    "value": flavor_text,
                    "inline": True,
                }
            )

        if fields:
            embed["fields"] = fields

        # Apply vendor branding (logos / colors)
        embed = apply_vendor_branding(embed, site_name)

        # Record state in seen cache
        seen[product_id] = {
            "first_seen": now_str,
            "title": title,
            "url": url,
            "site": site_name,
            "last_price": price,
            "last_in_stock": in_stock,
            "last_seen": now_str,
            "image_url": image_url or "",
            "normalized_title": normalized_title,
        }

        # Send main drop post
        send_discord_message(msg, product_type, embed)

    return seen


def main():
    print("[INFO] Starting product watcher (auto-classifying types + drop calendar)...")
    seen = load_seen()
    db_url = get_database_url()
    print(f"[INFO] DB URL loaded (masked): {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"[INFO] Loaded {len(seen)} previously-seen products.")

    # Load stored drop events (email + manual from past runs)
    drop_events = load_drop_events()
    print(f"[INFO] Loaded {len(drop_events)} previously scheduled drop event(s).")

    # Optional: prompt for manual drops at startup
    drop_events = prompt_manual_drops(drop_events)
    save_drop_events(drop_events)

    last_email_check_time = 0.0

    while True:
        loop_time = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        print(f"\n[INFO] Check loop at {loop_time}")

        # 1) Check sites for new products
        for site in SITES:
            print(f"[INFO] Checking {site['name']} -> {site['url']}")

            before = dict(seen)  # snapshot for delta detection
            seen = check_site(site, seen)

            # Compute delta: anything new or changed
            delta = {}
            for pid, data in seen.items():
                if before.get(pid) != data:
                    delta[pid] = data

            # Upsert delta into backend DB
            if delta:
                try:
                    sync_seen_to_db(delta)
                    print(f"[INFO] Synced {len(delta)} product(s) to DB.")
                except Exception as e:
                    print(f"[ERROR] DB sync failed: {e}")

            save_seen(seen)
            seen = load_seen()

        try:
            res = sync_seen_to_db(seen)
            print(f"[DB] Sync complete: inserted={res['inserted']} updated={res['updated']} skipped={res['skipped']}")
        except Exception as e:
            print(f"[DB] Sync failed: {e}")
        # 2) Check email for new drop announcements
        drop_events, last_email_check_time = check_email_for_drops(drop_events, last_email_check_time)

        # 3) Run drop reminder scheduler
        drop_events = check_drop_reminders(drop_events)
        save_drop_events(drop_events)

        print(f"[INFO] Sleeping {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
