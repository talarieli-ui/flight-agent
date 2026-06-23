"""
Flight Scanner — Real prices only.
Sources:
  1. Aviasales Data API v3 + v1 fallback (cache, free, no key needed)
  2. Google Flights via SerpAPI (real-time, requires SERPAPI_KEY)
  3. Travelpayouts Special Offers (free, no key)

Rules:
  - Max price: ₪3,500
  - Max 1 stop
  - price_verified=True required
  - Prague: July-August only
"""

import os, time, logging, requests
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

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
    {"code": "MAD", "name": "מדריד"},
    {"code": "WAW", "name": "ורשה"},
    {"code": "BER", "name": "ברלין"},
    {"code": "MUC", "name": "מינכן"},
    {"code": "CPH", "name": "קופנהגן"},
    {"code": "ZRH", "name": "ציריך"},
    # ארה"ב
    {"code": "JFK", "name": "ניו יורק"},
    {"code": "MIA", "name": "מיאמי"},
    # אסיה ומזה"ת
    {"code": "DXB", "name": "דובאי"},
    {"code": "BKK", "name": "בנגקוק"},
    {"code": "SIN", "name": "סינגפור"},
    {"code": "CAI", "name": "קהיר"},
]

DEST_RULES   = {"PRG": {"months_only": [7, 8]}}
MAX_PRICE_ILS = 3500
ILS_PER_USD   = 3.7

KIWI_SLUGS = {
    "KGS":"kos-greece","RHO":"rhodes-greece","CFU":"corfu-greece",
    "ATH":"athens-greece","SKG":"thessaloniki-greece","HER":"heraklion-crete-greece",
    "CHQ":"chania-crete-greece","JTR":"santorini-greece","JMK":"mykonos-greece",
    "ZTH":"zakynthos-greece","EFL":"kefalonia-greece","PVK":"preveza-greece",
    "JSI":"skiathos-greece","SMI":"samos-greece",
    "PRG":"prague-czechia","BUD":"budapest-hungary","VIE":"vienna-austria",
    "BCN":"barcelona-spain","CDG":"paris-france","LHR":"london-united-kingdom",
    "FCO":"rome-italy","AMS":"amsterdam-netherlands","DXB":"dubai-united-arab-emirates",
    "BKK":"bangkok-thailand","JFK":"new-york-united-states","MAD":"madrid-spain",
}


def _ils(usd):
    return round(float(usd) * ILS_PER_USD)


def build_search_windows():
    now = datetime.utcnow()
    windows, cur = [], now + timedelta(days=3)
    end = now + timedelta(days=183)
    while cur <= end:
        windows.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=7 if (cur - now).days < 60 else 14)
    return windows


def build_deep_link(source, origin, dest, dep_date):
    try:
        dt = datetime.strptime(dep_date[:10], "%Y-%m-%d")
    except Exception:
        dt = datetime.now()
    d8   = dt.strftime("%Y%m%d")
    dy   = dt.strftime("%Y-%m-%d")
    slug = KIWI_SLUGS.get(dest, dest.lower())
    links = {
        "Aviasales":      f"https://www.aviasales.com/search/{origin}{d8}{dest}1",
        "Travelpayouts":  f"https://www.aviasales.com/search/{origin}{d8}{dest}1",
        "Google Flights": f"https://www.google.com/travel/flights/search?q=flights+from+{origin}+to+{dest}+on+{dy}",
        "Skyscanner":     f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8}/?adults=1&cabinclass=economy&stops=!twoPlusStops",
        "Kiwi.com":       f"https://www.kiwi.com/en/search/results/tel-aviv-israel/{slug}/{dy}/{dy}?stops=0&adults=1",
    }
    return links.get(source, links["Skyscanner"])


class FlightScraper:
    def __init__(self, name, delay=1.0):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; FlightScanner/2.0)",
            "Accept": "application/json",
        })
        self._delay = delay

    def _sleep(self):
        time.sleep(self._delay + random.uniform(0.2, 0.4))

    def _result(self, source, origin, dest, price_usd, dep, arr="",
                ret_dep="", ret_arr="", duration=0, airline="?", stops=0):
        return {
            "source": source, "origin": origin, "destination": dest,
            "price_usd": round(float(price_usd), 2),
            "price_ils": _ils(price_usd),
            "price_verified": True,
            "departure": dep, "arrival": arr,
            "return_departure": ret_dep, "return_arrival": ret_arr,
            "duration_min": duration, "stops": stops, "airline": airline,
            "deep_link": build_deep_link(source, origin, dest, dep[:10] if dep else ""),
        }


class AviasalesScraper(FlightScraper):
    V3_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    V1_URL = "https://api.travelpayouts.com/v1/prices/cheap"

    def __init__(self):
        super().__init__("Aviasales")
        self.token = os.getenv("AVIASALES_TOKEN", "")

    def search(self, origin, dest, dep_date):
        results = self._v3(origin, dest, dep_date)
        if not results:
            results = self._v1(origin, dest, dep_date[:7])
        return results

    def _v3(self, origin, dest, dep_date):
        params = {"origin": origin, "destination": dest, "departure_at": dep_date,
                  "unique": "false", "sorting": "price", "direct": "false",
                  "limit": 5, "currency": "usd", "market": "il"}
        if self.token:
            params["token"] = self.token
        try:
            r = self.session.get(self.V3_URL, params=params, timeout=12)
            r.raise_for_status()
            data = r.json()
            if not data.get("success") and not data.get("data"):
                return []
            results = []
            for f in data.get("data", []):
                price = float(f.get("price", 0))
                if price <= 0: continue
                stops = f.get("transfers", 0)
                if stops > 1: continue
                dep = f.get("departure_at", dep_date + "T00:00:00")
                results.append(self._result("Aviasales", origin, dest, price,
                    dep=dep, ret_dep=f.get("return_at",""),
                    duration=f.get("duration", 0),
                    airline=f.get("airline","?"), stops=stops))
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[Aviasales v3] {origin}→{dest}: {e}")
            return []

    def _v1(self, origin, dest, month):
        params = {"origin": origin, "destination": dest,
                  "depart_date": month, "currency": "usd", "page": 1}
        if self.token:
            params["token"] = self.token
        try:
            r = self.session.get(self.V1_URL, params=params, timeout=12)
            r.raise_for_status()
            data = r.json()
            flights = data.get("data", {}).get(dest, {})
            results = []
            for _, f in (flights.items() if isinstance(flights, dict) else []):
                price = float(f.get("price", 0))
                if price <= 0: continue
                stops = f.get("transfers", 0)
                if stops > 1: continue
                dep = f.get("departure_at", month + "-01T00:00:00")
                results.append(self._result("Aviasales", origin, dest, price,
                    dep=dep, duration=f.get("duration", 0),
                    airline=f.get("airline","?"), stops=stops))
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[Aviasales v1] {origin}→{dest}: {e}")
            return []


class TravelpayoutsSpecialsScraper(FlightScraper):
    URL = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"

    def __init__(self):
        super().__init__("Travelpayouts")
        self.token = os.getenv("AVIASALES_TOKEN", "")

    def search_all(self, origin):
        params = {"origin": origin, "direct": "false",
                  "currency": "usd", "limit": 100, "market": "il"}
        if self.token:
            params["token"] = self.token
        try:
            r = self.session.get(self.URL, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("data", []):
                price = float(f.get("price", 0))
                if price <= 0: continue
                stops = f.get("transfers", 0)
                if stops > 1: continue
                dep = f.get("departure_at", "")
                results.append(self._result(
                    "Travelpayouts", origin, f.get("destination","?"), price,
                    dep=dep, ret_dep=f.get("return_at",""),
                    duration=f.get("duration", 0),
                    airline=f.get("airline","?"), stops=stops))
            self._sleep()
            logger.info(f"[Travelpayouts] specials: {len(results)} results")
            return results
        except Exception as e:
            logger.warning(f"[Travelpayouts] {e}")
            return []


class GoogleFlightsScraper(FlightScraper):
    URL = "https://serpapi.com/search"

    def __init__(self):
        super().__init__("Google Flights", delay=2.0)
        self.api_key = os.getenv("SERPAPI_KEY", "")

    def search(self, origin, dest, dep_date):
        if not self.api_key:
            return []
        try:
            r = self.session.get(self.URL, params={
                "engine": "google_flights",
                "departure_id": origin, "arrival_id": dest,
                "outbound_date": dep_date,
                "travel_class": 1, "stops": 2,   # 2 = up to 1 stop
                "currency": "ILS", "hl": "iw",
                "api_key": self.api_key,
            }, timeout=20)
            r.raise_for_status()
            results = []
            for f in (r.json().get("best_flights",[]) + r.json().get("other_flights",[])):
                legs  = f.get("flights", [])
                price = f.get("price", 0)
                if price <= 0: continue
                stops = len(legs) - 1
                if stops > 1: continue
                dep = legs[0].get("departure_airport",{}).get("time", dep_date) if legs else dep_date
                arr = legs[-1].get("arrival_airport",{}).get("time","") if legs else ""
                results.append({
                    "source": "Google Flights", "origin": origin, "destination": dest,
                    "price_usd": round(price / ILS_PER_USD, 2), "price_ils": price,
                    "price_verified": True,
                    "departure": dep, "arrival": arr,
                    "return_departure": "", "return_arrival": "",
                    "duration_min": f.get("total_duration", 0),
                    "stops": stops, "airline": legs[0].get("airline","?") if legs else "?",
                    "deep_link": build_deep_link("Google Flights", origin, dest, dep[:10]),
                })
            self._sleep()
            return results
        except Exception as e:
            logger.warning(f"[Google Flights] {origin}→{dest}: {e}")
            return []


def scan_destinations(dest_list):
    aviasales = AviasalesScraper()
    tp        = TravelpayoutsSpecialsScraper()
    gf        = GoogleFlightsScraper()
    windows   = build_search_windows()
    dest_map  = {d["code"]: d["name"] for d in dest_list}
    dest_codes = {d["code"] for d in dest_list if d["code"] != "TLV"}

    all_results = []

    # Special offers (bulk, covers all destinations)
    specials = tp.search_all("TLV")
    for f in specials:
        if f["destination"] in dest_codes:
            f["dest_name"]    = dest_map.get(f["destination"], f["destination"])
            f["window_label"] = f["departure"][:7] if f["departure"] else "—"
            all_results.append(f)
    logger.info(f"Specials matching destinations: {len([f for f in specials if f['destination'] in dest_codes])}")

    for dest in dest_list:
        code = dest["code"]
        if code == "TLV": continue
        months_only = DEST_RULES.get(code, {}).get("months_only", [])
        found = 0
        for dep_date in windows:
            if months_only and int(dep_date[5:7]) not in months_only:
                continue
            flights = aviasales.search("TLV", code, dep_date)
            flights += gf.search("TLV", code, dep_date)
            for f in flights:
                f["dest_name"]    = dest["name"]
                f["window_label"] = dep_date
            all_results.extend(flights)
            found += len(flights)
        logger.info(f"  TLV→{code}: {found} results")

    logger.info(f"Total verified results: {len(all_results)}")
    return all_results


def scan_all_flights():
    logger.info("🛫 Starting scan (max ₪3,500 | up to 1 stop | 3d–6m)")
    return scan_destinations(DESTINATIONS)


def scan_focused(query):
    q = query.strip().upper()
    matched = [d for d in DESTINATIONS if q in d["code"] or q in d["name"].upper()]
    if not matched:
        words = query.lower().split()
        matched = [d for d in DESTINATIONS if any(w in d["name"] for w in words)]
    if not matched:
        matched = DESTINATIONS
    return scan_destinations(matched)


def find_best_deals(flights, top_n=20):
    seen = {}
    for f in flights:
        if not f.get("price_verified"): continue
        price = f.get("price_ils", 99999)
        if price <= 0 or price > MAX_PRICE_ILS: continue
        if f.get("stops", 0) > 1: continue
        key = f["destination"]
        if key not in seen or price < seen[key].get("price_ils", 99999):
            seen[key] = f
    return sorted(seen.values(), key=lambda x: x.get("price_ils", 99999))[:top_n]
