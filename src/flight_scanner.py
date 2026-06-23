"""
Flight Scanner Agent - סוכן סריקת טיסות
Scans flight prices from Israel and sends email reports twice daily.
Supports focused scanning for a specific destination on demand.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ─── Destinations ─────────────────────────────────────────────────────────────

DESTINATIONS = [
    # אירופה
    {"code": "LHR", "name": "לונדון"},
    {"code": "CDG", "name": "פריז"},
    {"code": "FCO", "name": "רומא"},
    {"code": "BCN", "name": "ברצלונה"},
    {"code": "AMS", "name": "אמסטרדם"},
    {"code": "VIE", "name": "וינה"},
    {"code": "PRG", "name": "פראג"},
    {"code": "BUD", "name": "בודפשט"},
    {"code": "ATH", "name": "אתונה"},
    {"code": "DUB", "name": "דבלין"},
    {"code": "LIS", "name": "ליסבון"},
    {"code": "MXP", "name": "מילאנו"},
    {"code": "MAD", "name": "מדריד"},
    {"code": "WAW", "name": "ורשה"},
    {"code": "BER", "name": "ברלין"},
    {"code": "MUC", "name": "מינכן"},
    {"code": "CPH", "name": "קופנהגן"},
    {"code": "ARN", "name": "סטוקהולם"},
    {"code": "OSL", "name": "אוסלו"},
    {"code": "HEL", "name": "הלסינקי"},
    {"code": "ZRH", "name": "ציריך"},
    {"code": "GVA", "name": "ז'נבה"},
    {"code": "BRU", "name": "בריסל"},
    {"code": "SKG", "name": "סלוניקי"},
    {"code": "HER", "name": "כרתים"},
    {"code": "OTP", "name": "בוקרשט"},
    {"code": "SOF", "name": "סופיה"},
    # ארה"ב וקנדה
    {"code": "JFK", "name": "ניו יורק"},
    {"code": "LAX", "name": "לוס אנג'לס"},
    {"code": "MIA", "name": "מיאמי"},
    {"code": "ORD", "name": "שיקגו"},
    {"code": "YYZ", "name": "טורונטו"},
    # אסיה
    {"code": "DXB", "name": "דובאי"},
    {"code": "BKK", "name": "בנגקוק"},
    {"code": "NRT", "name": "טוקיו"},
    {"code": "SIN", "name": "סינגפור"},
    {"code": "HKG", "name": "הונג קונג"},
    {"code": "ICN", "name": "סיאול"},
    {"code": "DEL", "name": "דלהי"},
    {"code": "BOM", "name": "מומבאי"},
    # אפריקה
    {"code": "CAI", "name": "קהיר"},
    {"code": "CMN", "name": "קזבלנקה"},
    {"code": "CPT", "name": "קייפטאון"},
    {"code": "NBO", "name": "ניירובי"},
]

SEARCH_WINDOWS = [
    {"days_ahead": 7,  "label": "שבוע הקרוב"},
    {"days_ahead": 14, "label": "שבועיים"},
    {"days_ahead": 30, "label": "חודש קדימה"},
    {"days_ahead": 60, "label": "חודשיים קדימה"},
    {"days_ahead": 90, "label": "שלושה חודשים"},
]

BEST_BOOKING_TIPS = {
    "general": "מחקרים מראים שהזמנה 6–8 שבועות מראש נותנת את המחיר הטוב ביותר לרוב היעדים.",
    "best_days_to_book": ["שלישי", "רביעי"],
    "best_days_to_fly": ["שלישי", "רביעי", "שבת"],
    "worst_days_to_fly": ["שישי", "ראשון"],
    "best_time_to_search": "00:00–06:00 (לילה) — מחירים מתעדכנים בלילה ולרוב זולים יותר בבוקר מוקדם.",
    "kayak_tip": "השתמש ב-Kayak Explore לחיפוש יעדים זולים בטווח תאריכים גמיש.",
    "wizz_tip": "Wizz Air מוציאה מבצעים בדרך כלל ביום שלישי בצהריים. עקוב אחרי הניוזלטר שלהם.",
    "skyscanner_tip": "Skyscanner – השתמש ב-'כל החודש' ו-'מחיר הנמוך ביותר' כדי למצוא את היום הזול ביותר.",
    "hopper_tip": "Hopper חוזה מחירים עתידיים — מומלץ לבדוק ולהפעיל Price Freeze לנעילת מחיר.",
    "momondo_tip": "Momondo מציגה לוח מחירים חודשי ב-Cheapest Month — מצוין לגמישות.",
}

# ─── Scrapers ─────────────────────────────────────────────────────────────────

class FlightScraper:
    def __init__(self, name: str, delay: float = 1.5):
        self.name = name
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
        })

    def _sleep(self):
        time.sleep(self.delay + random.uniform(0.3, 0.8))


class SkypikerScraper(FlightScraper):
    """Kiwi / Tequila API — free tier, most reliable."""
    BASE_URL = "https://api.tequila.kiwi.com/v2/search"

    def __init__(self):
        super().__init__("Kiwi")
        api_key = os.getenv("KIWI_API_KEY", "")
        if api_key:
            self.session.headers["apikey"] = api_key

    def search(self, origin: str, dest: str, date_from: str, date_to: str) -> list[dict]:
        params = {
            "fly_from": origin, "fly_to": dest,
            "date_from": date_from, "date_to": date_to,
            "adults": 1, "selected_cabins": "M",
            "max_stopovers": 2, "limit": 5,
            "sort": "price", "curr": "ILS",
        }
        try:
            r = self.session.get(self.BASE_URL, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("data", [])[:5]:
                results.append({
                    "source": "Kiwi.com", "origin": origin, "destination": dest,
                    "price_ils": round(f.get("price", 0)),
                    "price_usd": round(f.get("price", 0) / 3.7),
                    "departure": f.get("local_departure", ""),
                    "arrival": f.get("local_arrival", ""),
                    "duration_min": f.get("duration", {}).get("total", 0) // 60,
                    "stops": len(f.get("route", [])) - 1,
                    "airline": f.get("airlines", ["?"])[0],
                    "deep_link": f.get("deep_link", "https://www.kiwi.com"),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class AviasalesScraper(FlightScraper):
    """Aviasales / Travelpayouts — free."""
    BASE_URL = "https://api.travelpayouts.com/v1/prices/cheap"

    def __init__(self):
        super().__init__("Aviasales")
        token = os.getenv("AVIASALES_TOKEN", "")
        if token:
            self.session.headers["X-Access-Token"] = token

    def search(self, origin: str, dest: str, month: str) -> list[dict]:
        try:
            r = self.session.get(self.BASE_URL, params={
                "origin": origin, "destination": dest,
                "depart_date": month, "currency": "usd", "page": 1,
            }, timeout=15)
            r.raise_for_status()
            flights = r.json().get("data", {}).get(dest, {})
            results = []
            for _, f in flights.items():
                results.append({
                    "source": "Aviasales", "origin": origin, "destination": dest,
                    "price_usd": f.get("price", 0),
                    "price_ils": round(f.get("price", 0) * 3.7),
                    "departure": f.get("departure_at", ""),
                    "arrival": f.get("return_at", ""),
                    "duration_min": f.get("duration", 0),
                    "stops": f.get("transfers", 0),
                    "airline": f.get("airline", "?"),
                    "deep_link": f"https://www.aviasales.com/search/{origin}{dest}1",
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class GoogleFlightsScraper(FlightScraper):
    """Google Flights via SerpAPI — 100 free searches/month."""
    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        super().__init__("Google Flights")
        self.api_key = os.getenv("SERPAPI_KEY", "")

    def search(self, origin: str, dest: str, departure_date: str) -> list[dict]:
        if not self.api_key:
            return []
        try:
            r = self.session.get(self.BASE_URL, params={
                "engine": "google_flights",
                "departure_id": origin, "arrival_id": dest,
                "outbound_date": departure_date,
                "currency": "ILS", "hl": "iw", "api_key": self.api_key,
            }, timeout=20)
            r.raise_for_status()
            results = []
            for f in r.json().get("best_flights", [])[:3]:
                price = f.get("price", 0)
                legs  = f.get("flights", [{}])
                results.append({
                    "source": "Google Flights", "origin": origin, "destination": dest,
                    "price_ils": price, "price_usd": round(price / 3.7),
                    "departure": legs[0].get("departure_airport", {}).get("time", ""),
                    "arrival": legs[-1].get("arrival_airport", {}).get("time", ""),
                    "duration_min": f.get("total_duration", 0),
                    "stops": len(legs) - 1,
                    "airline": legs[0].get("airline", "?"),
                    "deep_link": "https://www.google.com/travel/flights",
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class JetradarScraper(FlightScraper):
    """Jetradar / Aviasales partner feed — free."""
    BASE_URL = "https://api.travelpayouts.com/v1/prices/direct"

    def __init__(self):
        super().__init__("Jetradar")
        token = os.getenv("AVIASALES_TOKEN", "")
        if token:
            self.session.headers["X-Access-Token"] = token

    def search(self, origin: str, dest: str, month: str) -> list[dict]:
        try:
            r = self.session.get(self.BASE_URL, params={
                "origin": origin, "destination": dest,
                "depart_date": month, "currency": "usd",
            }, timeout=15)
            r.raise_for_status()
            flights = r.json().get("data", {}).get(dest, {})
            results = []
            for _, f in (flights.items() if isinstance(flights, dict) else []):
                results.append({
                    "source": "Jetradar", "origin": origin, "destination": dest,
                    "price_usd": f.get("price", 0),
                    "price_ils": round(f.get("price", 0) * 3.7),
                    "departure": f.get("departure_at", ""),
                    "arrival": "",
                    "duration_min": f.get("duration", 0),
                    "stops": 0,
                    "airline": f.get("airline", "?"),
                    "deep_link": f"https://www.jetradar.com/flights/{origin}-{dest}/",
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


# ─── Aggregator ───────────────────────────────────────────────────────────────

def scan_destinations(dest_list: list[dict]) -> list[dict]:
    """Scan a given list of destinations across all search windows."""
    kiwi      = SkypikerScraper()
    aviasales = AviasalesScraper()
    gf        = GoogleFlightsScraper()
    jetradar  = JetradarScraper()

    all_results = []
    now = datetime.utcnow()

    for dest in dest_list:
        dest_code = dest["code"]
        if dest_code == "TLV":
            continue

        for window in SEARCH_WINDOWS:
            target  = now + timedelta(days=window["days_ahead"])
            d_str   = target.strftime("%Y-%m-%d")
            d_from  = (target - timedelta(days=3)).strftime("%d/%m/%Y")
            d_to    = (target + timedelta(days=3)).strftime("%d/%m/%Y")
            month   = target.strftime("%Y-%m")

            flights = []
            flights += kiwi.search("TLV", dest_code, d_from, d_to)
            flights += aviasales.search("TLV", dest_code, month)
            flights += gf.search("TLV", dest_code, d_str)
            flights += jetradar.search("TLV", dest_code, month)

            for f in flights:
                f["dest_name"]    = dest["name"]
                f["window_label"] = window["label"]
                f["search_date"]  = d_str

            all_results.extend(flights)
            logger.info(f"  TLV→{dest_code} ({window['label']}): {len(flights)} results")

    return all_results


def scan_all_flights() -> list[dict]:
    logger.info("🛫 Starting full flight scan...")
    results = scan_destinations(DESTINATIONS)
    logger.info(f"✅ Full scan done. Total: {len(results)} results.")
    return results


def scan_focused(query: str) -> list[dict]:
    """
    Scan only destinations matching a city/country name or IATA code.
    query can be a free-text city/country name in Hebrew or English, or IATA code.
    """
    q = query.strip().upper()
    matched = [d for d in DESTINATIONS
               if q in d["code"].upper() or q in d["name"].upper() or q in d.get("name", "").lower()]
    if not matched:
        # Fuzzy: try substring of the query words
        words = query.lower().split()
        matched = [d for d in DESTINATIONS
                   if any(w in d["name"] for w in words)]
    if not matched:
        logger.warning(f"No destination match for query: '{query}' — scanning all.")
        matched = DESTINATIONS

    logger.info(f"🔍 Focused scan for '{query}' → {[d['code'] for d in matched]}")
    results = scan_destinations(matched)
    logger.info(f"✅ Focused scan done. {len(results)} results.")
    return results


def find_best_deals(flights: list[dict], top_n: int = 20) -> list[dict]:
    seen: dict = {}
    for f in flights:
        key = (f["destination"], f["window_label"])
        if key not in seen or f.get("price_ils", 99999) < seen[key].get("price_ils", 99999):
            seen[key] = f
    return sorted(seen.values(), key=lambda x: x.get("price_ils", 99999))[:top_n]
