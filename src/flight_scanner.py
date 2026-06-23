"""
Flight Scanner — Real prices only.
Sources:
  1. Aviasales Data API (cache, free, no key needed for basic)
  2. Google Flights via SerpAPI (requires SERPAPI_KEY, 100 free/month)
  3. Travelpayouts special offers (free, no key)

Kiwi/Tequila is excluded — blocks automated access.
No mock data. If a source returns nothing, nothing is displayed.
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

# ─── Destinations ─────────────────────────────────────────────────────────────

DESTINATIONS = [
    # איי יוון
    {"code": "KGS", "name": "קוס"},
    {"code": "RHO", "name": "רודוס"},
    {"code": "CFU", "name": "קורפו"},
    {"code": "EFL", "name": "קפלוניה"},
    {"code": "PVK", "name": "לפקדה / פרבזה"},
    {"code": "ZTH", "name": "זקינתוס"},
    {"code": "SKG", "name": "חלקידיקי / סלוניקי"},
    {"code": "JTR", "name": "סנטוריני"},
    {"code": "JMK", "name": "מיקונוס"},
    {"code": "HER", "name": "כרתים (הרקליון)"},
    {"code": "CHQ", "name": "כרתים (חניה)"},
    {"code": "JSI", "name": "סקיאתוס"},
    {"code": "SMI", "name": "סמוס"},
    {"code": "LXS", "name": "לסבוס"},
    {"code": "JKH", "name": "כיוס"},
    # אירופה
    {"code": "ATH", "name": "אתונה"},
    {"code": "LHR", "name": "לונדון"},
    {"code": "CDG", "name": "פריז"},
    {"code": "FCO", "name": "רומא"},
    {"code": "BCN", "name": "ברצלונה"},
    {"code": "AMS", "name": "אמסטרדם"},
    {"code": "VIE", "name": "וינה"},
    {"code": "PRG", "name": "פראג"},
    {"code": "BUD", "name": "בודפשט"},
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
    {"code": "ZRH", "name": "ציריך"},
    {"code": "BRU", "name": "בריסל"},
    {"code": "OTP", "name": "בוקרשט"},
    {"code": "SOF", "name": "סופיה"},
    # ארה"ב וקנדה
    {"code": "JFK", "name": "ניו יורק"},
    {"code": "LAX", "name": "לוס אנג'לס"},
    {"code": "MIA", "name": "מיאמי"},
    {"code": "ORD", "name": "שיקגו"},
    {"code": "YYZ", "name": "טורונטו"},
    # אסיה ומזה"ת
    {"code": "DXB", "name": "דובאי"},
    {"code": "BKK", "name": "בנגקוק"},
    {"code": "NRT", "name": "טוקיו"},
    {"code": "SIN", "name": "סינגפור"},
    {"code": "HKG", "name": "הונג קונג"},
    {"code": "ICN", "name": "סיאול"},
    # אפריקה
    {"code": "CAI", "name": "קהיר"},
    {"code": "CMN", "name": "קזבלנקה"},
]

# Special rules per destination
DEST_RULES = {
    "PRG": {"months_only": [7, 8]},   # פראג — יולי-אוגוסט בלבד
}

MAX_PRICE_ILS = 1200   # מסנן טיסות מעל ₪1,200
ILS_PER_USD   = 3.7    # שער המרה (מתעדכן)


def _ils(usd: float) -> int:
    return round(usd * ILS_PER_USD)


def build_search_windows():
    """3 days ahead → 6 months, sampled weekly then bi-weekly."""
    now   = datetime.utcnow()
    start = now + timedelta(days=3)
    end   = now + timedelta(days=183)
    windows, cur = [], start
    while cur <= end:
        windows.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=7 if (cur - start).days < 60 else 14)
    return windows


# ─── Deep-link builder ────────────────────────────────────────────────────────

KIWI_SLUGS = {
    "KGS":"kos-greece","RHO":"rhodes-greece","CFU":"corfu-greece",
    "ATH":"athens-greece","SKG":"thessaloniki-greece","HER":"heraklion-crete-greece",
    "CHQ":"chania-crete-greece","JTR":"santorini-greece","JMK":"mykonos-greece",
    "ZTH":"zakynthos-greece","EFL":"kefalonia-greece","PVK":"preveza-greece",
    "JSI":"skiathos-greece","SMI":"samos-greece","LXS":"lesbos-greece","JKH":"chios-greece",
    "PRG":"prague-czechia","BUD":"budapest-hungary","VIE":"vienna-austria",
    "BCN":"barcelona-spain","CDG":"paris-france","LHR":"london-united-kingdom",
    "FCO":"rome-italy","AMS":"amsterdam-netherlands","DXB":"dubai-united-arab-emirates",
    "BKK":"bangkok-thailand","JFK":"new-york-united-states","MAD":"madrid-spain",
}


def build_deep_link(source: str, origin: str, dest: str, dep_date: str) -> str:
    try:
        dt = datetime.strptime(dep_date[:10], "%Y-%m-%d")
    except Exception:
        dt = datetime.now()
    d8  = dt.strftime("%Y%m%d")
    dy  = dt.strftime("%Y-%m-%d")
    slug = KIWI_SLUGS.get(dest, f"{dest.lower()}")

    m = {
        "Aviasales":       f"https://www.aviasales.com/search/{origin}{d8}{dest}1",
        "Google Flights":  f"https://www.google.com/travel/flights/search?q=direct+flights+from+{origin}+to+{dest}+on+{dy}",
        "Skyscanner":      f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8}/?adults=1&cabinclass=economy&stops=!oneStop,!twoPlusStops",
        "Expedia":         f"https://www.expedia.com/Flights-Search?trip=oneway&leg1=from%3A{origin}%2Cto%3A{dest}%2Cdeparture%3A{d8}TANYT&passengers=adults%3A1&options=cabinclass%3Aeconomy%2Cmaxhops%3A0",
        "Kiwi.com":        f"https://www.kiwi.com/en/search/results/tel-aviv-israel/{slug}/{dy}/{dy}?stops=0&adults=1",
    }
    return m.get(source, m["Skyscanner"])


# ─── Scrapers ─────────────────────────────────────────────────────────────────

class FlightScraper:
    def __init__(self, name: str, delay: float = 1.0):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; FlightScanner/2.0)",
            "Accept": "application/json",
        })
        self._delay = delay

    def _sleep(self):
        time.sleep(self._delay + random.uniform(0.2, 0.5))

    def _make_result(self, source, origin, dest, price_usd,
                     dep, arr="", ret_dep="", ret_arr="",
                     duration=0, airline="?") -> dict:
        price_ils = _ils(price_usd)
        return {
            "source": source,
            "origin": origin,
            "destination": dest,
            "price_usd": round(price_usd, 2),
            "price_ils": price_ils,
            "price_verified": True,       # came from real API
            "departure": dep,
            "arrival": arr,
            "return_departure": ret_dep,
            "return_arrival": ret_arr,
            "duration_min": duration,
            "stops": 0,
            "airline": airline,
            "deep_link": build_deep_link(source, origin, dest, dep[:10] if dep else ""),
        }


class AviasalesDataScraper(FlightScraper):
    """
    Aviasales Data API — cached prices, free, no auth needed.
    Returns cheapest verified price per month.
    Docs: https://support.travelpayouts.com/hc/en-us/articles/203956163
    """
    BASE = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    def __init__(self):
        super().__init__("Aviasales")
        self.token = os.getenv("AVIASALES_TOKEN", "")

    def search(self, origin: str, dest: str, dep_date: str) -> list:
        params = {
            "origin":      origin,
            "destination": dest,
            "departure_at": dep_date,   # YYYY-MM-DD
            "unique":      "false",
            "sorting":     "price",
            "direct":      "true",
            "limit":       3,
            "currency":    "usd",
            "market":      "il",
        }
        if self.token:
            params["token"] = self.token

        try:
            r = self.session.get(self.BASE, params=params, timeout=12)
            r.raise_for_status()
            data = r.json()
            results = []
            for f in data.get("data", []):
                if f.get("transfers", 0) != 0:
                    continue
                price = float(f.get("price", 0))
                if price <= 0:
                    continue
                dep = f.get("departure_at", dep_date + "T00:00:00")
                results.append(self._make_result(
                    "Aviasales", origin, dest, price,
                    dep=dep,
                    ret_dep=f.get("return_at", ""),
                    duration=f.get("duration", 0),
                    airline=f.get("airline", "?"),
                ))
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[Aviasales] {origin}→{dest} {dep_date}: {e}")
            return []


class TravelpayoutsSpecialScraper(FlightScraper):
    """
    Travelpayouts special-offer prices — free, no key.
    Returns unusually low prices (deals/sales).
    """
    BASE = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"

    def __init__(self):
        super().__init__("Travelpayouts")
        self.token = os.getenv("AVIASALES_TOKEN", "")

    def search_all_from(self, origin: str) -> list:
        params = {
            "origin":   origin,
            "direct":   "true",
            "currency": "usd",
            "limit":    100,
            "market":   "il",
        }
        if self.token:
            params["token"] = self.token
        try:
            r = self.session.get(self.BASE, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("data", []):
                if f.get("transfers", 0) != 0:
                    continue
                price = float(f.get("price", 0))
                if price <= 0:
                    continue
                dep = f.get("departure_at", "")
                results.append({
                    **self._make_result("Travelpayouts", origin,
                                        f.get("destination", "?"), price,
                                        dep=dep,
                                        ret_dep=f.get("return_at", ""),
                                        duration=f.get("duration", 0),
                                        airline=f.get("airline", "?")),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[Travelpayouts specials] {origin}: {e}")
            return []


class GoogleFlightsScraper(FlightScraper):
    """
    Google Flights via SerpAPI — real-time verified prices.
    Requires SERPAPI_KEY. 100 free searches/month.
    """
    BASE = "https://serpapi.com/search"

    def __init__(self):
        super().__init__("Google Flights", delay=2.0)
        self.api_key = os.getenv("SERPAPI_KEY", "")

    def search(self, origin: str, dest: str, dep_date: str) -> list:
        if not self.api_key:
            return []
        try:
            r = self.session.get(self.BASE, params={
                "engine":        "google_flights",
                "departure_id":  origin,
                "arrival_id":    dest,
                "outbound_date": dep_date,
                "travel_class":  1,       # Economy
                "stops":         1,       # 1 = nonstop only
                "currency":      "ILS",
                "hl":            "iw",
                "api_key":       self.api_key,
            }, timeout=20)
            r.raise_for_status()
            results = []
            for f in r.json().get("best_flights", []):
                legs = f.get("flights", [])
                if len(legs) != 1:
                    continue
                price_ils = f.get("price", 0)
                if price_ils <= 0:
                    continue
                leg = legs[0]
                dep = leg.get("departure_airport", {}).get("time", dep_date)
                arr = leg.get("arrival_airport", {}).get("time", "")
                results.append({
                    "source": "Google Flights",
                    "origin": origin,
                    "destination": dest,
                    "price_usd": round(price_ils / ILS_PER_USD, 2),
                    "price_ils": price_ils,
                    "price_verified": True,
                    "departure": dep,
                    "arrival": arr,
                    "return_departure": "",
                    "return_arrival": "",
                    "duration_min": f.get("total_duration", 0),
                    "stops": 0,
                    "airline": leg.get("airline", "?"),
                    "deep_link": build_deep_link("Google Flights", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[Google Flights] {origin}→{dest}: {e}")
            return []


# ─── Aggregator ───────────────────────────────────────────────────────────────

def scan_destinations(dest_list: list) -> list:
    aviasales    = AviasalesDataScraper()
    tp_specials  = TravelpayoutsSpecialScraper()
    gf           = GoogleFlightsScraper()
    windows      = build_search_windows()

    logger.info(f"Windows: {len(windows)} dates, {windows[0]} → {windows[-1]}")

    # Get special offers once (covers all destinations)
    specials = tp_specials.search_all_from("TLV")
    logger.info(f"Special offers: {len(specials)} direct flights")

    # Build a set of dest codes we care about
    dest_codes = {d["code"] for d in dest_list if d["code"] != "TLV"}
    dest_map   = {d["code"]: d["name"] for d in dest_list}

    # Filter specials to our destinations
    all_results = []
    for f in specials:
        if f["destination"] in dest_codes:
            f["dest_name"]    = dest_map.get(f["destination"], f["destination"])
            f["window_label"] = f["departure"][:7] if f["departure"] else ""
            all_results.append(f)

    # Per-destination date-based search
    for dest in dest_list:
        dest_code = dest["code"]
        if dest_code == "TLV":
            continue
        rules       = DEST_RULES.get(dest_code, {})
        months_only = rules.get("months_only", [])

        for dep_date in windows:
            if months_only and int(dep_date[5:7]) not in months_only:
                continue

            flights = []
            flights += aviasales.search("TLV", dest_code, dep_date)
            flights += gf.search("TLV", dest_code, dep_date)

            for f in flights:
                f["dest_name"]    = dest["name"]
                f["window_label"] = dep_date
            all_results.extend(flights)

        logger.info(f"  TLV→{dest_code} done")

    return all_results


def scan_all_flights() -> list:
    logger.info("🛫 Starting real-price scan (direct only, no mock data)...")
    results = scan_destinations(DESTINATIONS)
    logger.info(f"✅ Done. {len(results)} verified results.")
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
    """
    Best verified deal per destination.
    - Direct only (stops=0)
    - Max ₪1,200
    - Must have price_verified=True
    Sorted price low→high.
    """
    seen: dict = {}
    for f in flights:
        if f.get("stops", 0) != 0:
            continue
        if not f.get("price_verified", False):
            continue                          # skip unverified prices
        price = f.get("price_ils", 99999)
        if price <= 0 or price > MAX_PRICE_ILS:
            continue
        key = f["destination"]
        if key not in seen or price < seen[key].get("price_ils", 99999):
            seen[key] = f
    return sorted(seen.values(), key=lambda x: x.get("price_ils", 99999))[:top_n]
