"""
Flight Scanner Agent - סוכן סריקת טיסות
Scans flight prices from Israel. Search window: 4-6 days ahead only.
"""

import os
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
    {"code": "JFK", "name": "ניו יורק"},
    {"code": "LAX", "name": "לוס אנג'לס"},
    {"code": "MIA", "name": "מיאמי"},
    {"code": "ORD", "name": "שיקגו"},
    {"code": "YYZ", "name": "טורונטו"},
    {"code": "DXB", "name": "דובאי"},
    {"code": "BKK", "name": "בנגקוק"},
    {"code": "NRT", "name": "טוקיו"},
    {"code": "SIN", "name": "סינגפור"},
    {"code": "HKG", "name": "הונג קונג"},
    {"code": "ICN", "name": "סיאול"},
    {"code": "DEL", "name": "דלהי"},
    {"code": "BOM", "name": "מומבאי"},
    {"code": "CAI", "name": "קהיר"},
    {"code": "CMN", "name": "קזבלנקה"},
    {"code": "CPT", "name": "קייפטאון"},
    {"code": "NBO", "name": "ניירובי"},
]

# Search window: 4–6 days ahead only
SEARCH_WINDOWS = [
    {"days_ahead": 4, "label": "4 ימים"},
    {"days_ahead": 5, "label": "5 ימים"},
    {"days_ahead": 6, "label": "6 ימים"},
]


def _make_deep_link(source: str, origin: str, dest_code: str, departure_date: str) -> str:
    """
    Build a deep link that opens the booking site pre-filled with
    origin=TLV, destination, and departure date.
    departure_date format: 'YYYY-MM-DD'
    """
    try:
        dt = datetime.strptime(departure_date[:10], "%Y-%m-%d")
    except Exception:
        dt = datetime.now()

    date_yyyymmdd = dt.strftime("%Y%m%d")   # 20260710
    date_ddmmyyyy = dt.strftime("%d/%m/%Y")  # 10/07/2026
    date_yyyy_mm_dd = dt.strftime("%Y-%m-%d") # 2026-07-10
    month_yyyy_mm = dt.strftime("%Y-%m")      # 2026-07

    if source == "Kiwi.com":
        # Kiwi deep search link
        return (
            f"https://www.kiwi.com/en/search/results/"
            f"tel-aviv-israel/{dest_code.lower()}-airport/"
            f"{date_yyyy_mm_dd}/{date_yyyy_mm_dd}"
        )
    elif source == "Aviasales":
        return (
            f"https://www.aviasales.com/search/"
            f"{origin}{date_yyyymmdd}{dest_code}1"
        )
    elif source == "Jetradar":
        return (
            f"https://www.jetradar.com/flights/"
            f"{origin}-{dest_code}/?depart_date={date_yyyy_mm_dd}"
        )
    elif source == "Google Flights":
        return (
            f"https://www.google.com/travel/flights/search"
            f"?tfs=CBwQAhoeEgoyMDI2LTA3LTEwagcIARIDVExWcgcIARIDTEhSQAFIAXABggELCP___________wGYAQI"
            # Simpler reliable URL:
        )
    else:
        # Generic Skyscanner deep link
        return (
            f"https://www.skyscanner.net/transport/flights/"
            f"{origin.lower()}/{dest_code.lower()}/{date_yyyymmdd}/"
            f"?adults=1&cabinclass=economy"
        )


class FlightScraper:
    def __init__(self, name: str, delay: float = 1.2):
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
        time.sleep(self.delay + random.uniform(0.2, 0.6))


class SkypikerScraper(FlightScraper):
    BASE_URL = "https://api.tequila.kiwi.com/v2/search"

    def __init__(self):
        super().__init__("Kiwi.com")
        api_key = os.getenv("KIWI_API_KEY", "")
        if api_key:
            self.session.headers["apikey"] = api_key

    def search(self, origin: str, dest: str, departure_date: str) -> list:
        # Search exactly on that date ±0 days
        date_fmt = datetime.strptime(departure_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        params = {
            "fly_from": origin, "fly_to": dest,
            "date_from": date_fmt, "date_to": date_fmt,
            "adults": 1, "selected_cabins": "M",
            "max_stopovers": 2, "limit": 3,
            "sort": "price", "curr": "ILS",
        }
        try:
            r = self.session.get(self.BASE_URL, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("data", [])[:3]:
                dep = f.get("local_departure", departure_date)
                results.append({
                    "source": "Kiwi.com",
                    "origin": origin, "destination": dest,
                    "price_ils": round(f.get("price", 0)),
                    "departure": dep,
                    "arrival": f.get("local_arrival", ""),
                    "duration_min": f.get("duration", {}).get("total", 0) // 60,
                    "stops": max(0, len(f.get("route", [])) - 1),
                    "airline": f.get("airlines", ["?"])[0],
                    "deep_link": f.get("deep_link") or _make_deep_link("Kiwi.com", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class AviasalesScraper(FlightScraper):
    BASE_URL = "https://api.travelpayouts.com/v1/prices/cheap"

    def __init__(self):
        super().__init__("Aviasales")
        token = os.getenv("AVIASALES_TOKEN", "")
        if token:
            self.session.headers["X-Access-Token"] = token

    def search(self, origin: str, dest: str, departure_date: str) -> list:
        month = departure_date[:7]  # YYYY-MM
        try:
            r = self.session.get(self.BASE_URL, params={
                "origin": origin, "destination": dest,
                "depart_date": month, "currency": "usd", "page": 1,
            }, timeout=15)
            r.raise_for_status()
            flights = r.json().get("data", {}).get(dest, {})
            results = []
            for _, f in (flights.items() if isinstance(flights, dict) else []):
                dep = f.get("departure_at", departure_date)
                results.append({
                    "source": "Aviasales",
                    "origin": origin, "destination": dest,
                    "price_usd": f.get("price", 0),
                    "price_ils": round(f.get("price", 0) * 3.7),
                    "departure": dep,
                    "arrival": "",
                    "duration_min": f.get("duration", 0),
                    "stops": f.get("transfers", 0),
                    "airline": f.get("airline", "?"),
                    "deep_link": _make_deep_link("Aviasales", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class GoogleFlightsScraper(FlightScraper):
    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        super().__init__("Google Flights")
        self.api_key = os.getenv("SERPAPI_KEY", "")

    def search(self, origin: str, dest: str, departure_date: str) -> list:
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
                dep   = legs[0].get("departure_airport", {}).get("time", departure_date)
                results.append({
                    "source": "Google Flights",
                    "origin": origin, "destination": dest,
                    "price_ils": price, "price_usd": round(price / 3.7),
                    "departure": dep,
                    "arrival": legs[-1].get("arrival_airport", {}).get("time", ""),
                    "duration_min": f.get("total_duration", 0),
                    "stops": len(legs) - 1,
                    "airline": legs[0].get("airline", "?"),
                    "deep_link": _make_deep_link("Google Flights", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


# ─── Aggregator ───────────────────────────────────────────────────────────────

def scan_destinations(dest_list: list) -> list:
    kiwi      = SkypikerScraper()
    aviasales = AviasalesScraper()
    gf        = GoogleFlightsScraper()

    all_results = []
    now = datetime.utcnow()

    for dest in dest_list:
        dest_code = dest["code"]
        if dest_code == "TLV":
            continue

        for window in SEARCH_WINDOWS:
            target_date = (now + timedelta(days=window["days_ahead"])).strftime("%Y-%m-%d")

            flights = []
            flights += kiwi.search("TLV", dest_code, target_date)
            flights += aviasales.search("TLV", dest_code, target_date)
            flights += gf.search("TLV", dest_code, target_date)

            for f in flights:
                f["dest_name"]    = dest["name"]
                f["window_label"] = window["label"]
                f["search_date"]  = target_date

            all_results.extend(flights)

        logger.info(f"  TLV→{dest_code}: done")

    return all_results


def scan_all_flights() -> list:
    logger.info("🛫 Starting full flight scan (4–6 days window)...")
    results = scan_destinations(DESTINATIONS)
    logger.info(f"✅ Scan complete. Total: {len(results)} results.")
    return results


def scan_focused(query: str) -> list:
    q = query.strip().upper()
    matched = [d for d in DESTINATIONS
               if q in d["code"].upper() or q in d["name"].upper()]
    if not matched:
        words = query.lower().split()
        matched = [d for d in DESTINATIONS if any(w in d["name"] for w in words)]
    if not matched:
        matched = DESTINATIONS
    logger.info(f"🔍 Focused scan: '{query}' → {[d['code'] for d in matched]}")
    return scan_destinations(matched)


def find_best_deals(flights: list, top_n: int = 20) -> list:
    """Return top N cheapest deals, sorted price low→high."""
    seen: dict = {}
    for f in flights:
        key = (f["destination"], f.get("window_label",""))
        if key not in seen or f.get("price_ils", 99999) < seen[key].get("price_ils", 99999):
            seen[key] = f
    # Sort by price ascending
    return sorted(seen.values(), key=lambda x: x.get("price_ils", 99999))[:top_n]
