"""
Flight Scanner Agent
- Search window: 3 days ahead → 6 months ahead
- Direct flights only (stops=0)
- Returns departure + return date/time
"""

import os
import time
import logging
import requests
from datetime import datetime, timedelta
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

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
    # איי יוון
    {"code": "EFL", "name": "קפלוניה"},
    {"code": "CFU", "name": "קורפו"},
    {"code": "PVK", "name": "לפקדה / פרבזה"},
    {"code": "ZTH", "name": "זקינתוס"},
    {"code": "KGS", "name": "קוס"},
    {"code": "RHO", "name": "רודוס"},
    {"code": "JMK", "name": "מיקונוס"},
    {"code": "JTR", "name": "סנטוריני"},
    {"code": "HER", "name": "כרתים (הרקליון)"},
    {"code": "CHQ", "name": "כרתים (חניה)"},
    {"code": "JSI", "name": "סקיאתוס"},
    {"code": "SMI", "name": "סמוס"},
    {"code": "LXS", "name": "לסבוס"},
    {"code": "JKH", "name": "כיוס"},
]

# --- Special rules per destination ---
# Prague: only July–August
# Max price: ₪1,200 (applied in find_best_deals)
DEST_RULES = {
    "PRG": {"months_only": [7, 8]},   # פראג — יולי-אוגוסט בלבד
}

MAX_PRICE_ILS = 1200   # מסנן טיסות מעל ₪1,200

# Search: from 3 days ahead to 6 months ahead, sampled at intervals
def build_search_windows():
    now = datetime.utcnow()
    start = now + timedelta(days=3)
    end   = now + timedelta(days=183)   # ~6 months
    windows = []
    current = start
    # Weekly intervals for the first 2 months, then bi-weekly
    while current <= end:
        days_ahead = (current - now).days
        if days_ahead <= 60:
            step = 7
        else:
            step = 14
        windows.append({
            "date": current.strftime("%Y-%m-%d"),
            "label": _date_label(current),
        })
        current += timedelta(days=step)
    return windows


def _date_label(dt: datetime) -> str:
    months_he = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                 "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    return f"{dt.day} {months_he[dt.month]}"


def build_deep_link(source: str, origin: str, dest_code: str, departure_date: str) -> str:
    try:
        dt = datetime.strptime(departure_date[:10], "%Y-%m-%d")
    except Exception:
        dt = datetime.now()
    d8  = dt.strftime("%Y%m%d")
    dy  = dt.strftime("%Y-%m-%d")
    links = {
        "Kiwi.com": (
            f"https://www.kiwi.com/en/search/results/"
            f"tel-aviv-israel/{dest_code.lower()}-airport/{dy}/{dy}"
            f"?adults=1&cabinClass=ECONOMY"
        ),
        "Aviasales": f"https://www.aviasales.com/search/{origin}{d8}{dest_code}1",
        "Jetradar":  f"https://www.jetradar.com/flights/{origin}-{dest_code}/?depart_date={dy}",
        "Google Flights": (
            f"https://www.google.com/travel/flights/search"
            f"?q=flights+from+{origin}+to+{dest_code}+on+{dy}"
        ),
    }
    return links.get(source,
        f"https://www.skyscanner.net/transport/flights/"
        f"{origin.lower()}/{dest_code.lower()}/{d8}/?adults=1&cabinclass=economy"
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
        time.sleep(self.delay + random.uniform(0.2, 0.5))


class SkypikerScraper(FlightScraper):
    BASE_URL = "https://api.tequila.kiwi.com/v2/search"

    def __init__(self):
        super().__init__("Kiwi.com")
        api_key = os.getenv("KIWI_API_KEY", "")
        if api_key:
            self.session.headers["apikey"] = api_key

    def search(self, origin: str, dest: str, departure_date: str) -> list:
        dt = datetime.strptime(departure_date, "%Y-%m-%d")
        date_fmt = dt.strftime("%d/%m/%Y")
        params = {
            "fly_from": origin, "fly_to": dest,
            "date_from": date_fmt, "date_to": date_fmt,
            "adults": 1, "selected_cabins": "M",
            "max_stopovers": 0,          # ← direct only
            "limit": 5,
            "sort": "price", "curr": "ILS",
        }
        try:
            r = self.session.get(self.BASE_URL, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("data", []):
                if len(f.get("route", [])) > 1:   # double-check direct
                    continue
                dep = f.get("local_departure", departure_date + "T00:00:00")
                arr = f.get("local_arrival", "")
                results.append({
                    "source": "Kiwi.com",
                    "origin": origin, "destination": dest,
                    "price_ils": round(f.get("price", 0)),
                    "price_verified": True,     # price came from real API
                    "departure": dep,
                    "arrival":   arr,
                    "return_departure": "",
                    "return_arrival":   "",
                    "duration_min": f.get("duration", {}).get("total", 0) // 60,
                    "stops": 0,
                    "airline": f.get("airlines", ["?"])[0],
                    "deep_link": f.get("deep_link") or build_deep_link("Kiwi.com", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest} {departure_date}: {e}")
            return []


class AviasalesScraper(FlightScraper):
    BASE_URL = "https://api.travelpayouts.com/v1/prices/cheap"

    def __init__(self):
        super().__init__("Aviasales")
        token = os.getenv("AVIASALES_TOKEN", "")
        if token:
            self.session.headers["X-Access-Token"] = token

    def search(self, origin: str, dest: str, departure_date: str) -> list:
        month = departure_date[:7]
        try:
            r = self.session.get(self.BASE_URL, params={
                "origin": origin, "destination": dest,
                "depart_date": month, "currency": "usd", "page": 1,
                "direct": "true",        # ← direct only
            }, timeout=15)
            r.raise_for_status()
            flights = r.json().get("data", {}).get(dest, {})
            results = []
            for _, f in (flights.items() if isinstance(flights, dict) else []):
                if f.get("transfers", 0) != 0:
                    continue
                dep = f.get("departure_at", departure_date + "T00:00:00")
                results.append({
                    "source": "Aviasales",
                    "origin": origin, "destination": dest,
                    "price_usd": f.get("price", 0),
                    "price_ils": round(f.get("price", 0) * 3.7),
                    "departure": dep,
                    "arrival":   "",
                    "return_departure": f.get("return_at", ""),
                    "return_arrival":   "",
                    "duration_min": f.get("duration", 0),
                    "stops": 0,
                    "airline": f.get("airline", "?"),
                    "deep_link": build_deep_link("Aviasales", origin, dest, dep[:10]),
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
                "stops": "1",            # ← 1 = nonstop only in SerpAPI
                "currency": "ILS", "hl": "iw", "api_key": self.api_key,
            }, timeout=20)
            r.raise_for_status()
            results = []
            for f in r.json().get("best_flights", []):
                legs = f.get("flights", [])
                if len(legs) != 1:       # direct = exactly 1 leg
                    continue
                price = f.get("price", 0)
                dep   = legs[0].get("departure_airport", {}).get("time", departure_date)
                arr   = legs[0].get("arrival_airport", {}).get("time", "")
                results.append({
                    "source": "Google Flights",
                    "origin": origin, "destination": dest,
                    "price_ils": price,
                    "departure": dep,
                    "arrival":   arr,
                    "return_departure": "",
                    "return_arrival":   "",
                    "duration_min": f.get("total_duration", 0),
                    "stops": 0,
                    "airline": legs[0].get("airline", "?"),
                    "deep_link": build_deep_link("Google Flights", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class ExpediaScraper(FlightScraper):
    """Expedia Rapid API — paid but free tier available."""
    BASE_URL = "https://test.api.expedia.com/flights/v3/search"

    def __init__(self):
        super().__init__("Expedia")
        self.api_key = os.getenv("EXPEDIA_API_KEY", "")
        self.api_secret = os.getenv("EXPEDIA_API_SECRET", "")

    def search(self, origin: str, dest: str, departure_date: str) -> list:
        if not self.api_key:
            return []
        try:
            import hashlib, time as t
            ts = str(int(t.time()))
            sig = hashlib.md5(f"{self.api_key}{ts}{self.api_secret}".encode()).hexdigest()
            r = self.session.get(self.BASE_URL, params={
                "departureAirport": origin,
                "arrivalAirport": dest,
                "departureDate": departure_date,
                "adults": 1,
                "nonstop": True,
                "currency": "ILS",
                "apiKey": self.api_key,
                "cid": ts,
                "sig": sig,
            }, timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("offers", [])[:3]:
                price = f.get("totalFare", {}).get("totalFare", 0)
                seg   = f.get("legs", [{}])[0].get("segments", [{}])[0]
                dep   = seg.get("departureDateTime", departure_date + "T00:00:00")
                arr   = seg.get("arrivalDateTime", "")
                from email_builder import build_deep_link
                results.append({
                    "source": "Expedia",
                    "origin": origin, "destination": dest,
                    "price_ils": round(price),
                    "departure": dep, "arrival": arr,
                    "return_departure": "", "return_arrival": "",
                    "duration_min": f.get("totalTripTime", 0),
                    "stops": 0,
                    "airline": seg.get("marketingCarrier", {}).get("code", "?"),
                    "deep_link": build_deep_link("Expedia", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[{self.name}] {origin}→{dest}: {e}")
            return []


class EDreamsScraper(FlightScraper):
    """
    eDreams / Opodo partner API via Travelpayouts affiliate feed.
    Falls back to link-only if no token.
    """

    def __init__(self):
        super().__init__("eDreams")

    def search(self, origin: str, dest: str, departure_date: str) -> list:
        # eDreams doesn't expose a free search API — returns link-only entries
        # so the user gets directed to eDreams with pre-filled params
        return []   # populated as a booking link option in email_builder


def scan_destinations(dest_list: list) -> list:
    kiwi      = SkypikerScraper()
    aviasales = AviasalesScraper()
    gf        = GoogleFlightsScraper()
    expedia   = ExpediaScraper()
    windows   = build_search_windows()

    logger.info(f"Search windows: {len(windows)} dates from {windows[0]['date']} to {windows[-1]['date']}")

    all_results = []
    for dest in dest_list:
        dest_code = dest["code"]
        if dest_code == "TLV":
            continue
        rules = DEST_RULES.get(dest_code, {})
        months_only = rules.get("months_only", [])

        for w in windows:
            # Apply month filter if defined for this destination
            if months_only:
                w_month = int(w["date"][5:7])
                if w_month not in months_only:
                    continue

            flights = []
            flights += kiwi.search("TLV", dest_code, w["date"])
            flights += aviasales.search("TLV", dest_code, w["date"])
            flights += gf.search("TLV", dest_code, w["date"])
            flights += expedia.search("TLV", dest_code, w["date"])
            for f in flights:
                f["dest_name"]    = dest["name"]
                f["window_label"] = w["label"]
                f["search_date"]  = w["date"]
            all_results.extend(flights)
        logger.info(f"  TLV→{dest_code}: done")
    return all_results


def scan_all_flights() -> list:
    logger.info("🛫 Starting full scan (direct only, 3 days → 6 months)...")
    results = scan_destinations(DESTINATIONS)
    logger.info(f"✅ Done. {len(results)} direct flights found.")
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
    logger.info(f"🔍 Focused: '{query}' → {[d['code'] for d in matched]}")
    return scan_destinations(matched)


def find_best_deals(flights: list, top_n: int = 20) -> list:
    """Best deal per destination (direct only, max ₪1,200), sorted price low→high."""
    seen: dict = {}
    for f in flights:
        if f.get("stops", 0) != 0:
            continue
        price = f.get("price_ils", 99999)
        if price > MAX_PRICE_ILS:
            continue   # מסנן טיסות מעל ₪1,200
        key = f["destination"]
        if key not in seen or price < seen[key].get("price_ils", 99999):
            seen[key] = f
    return sorted(seen.values(), key=lambda x: x.get("price_ils", 99999))[:top_n]
