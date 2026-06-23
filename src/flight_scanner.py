"""
Flight Scanner — Real prices via SerpAPI (Google Flights).
Aviasales as secondary source.
Verified prices only. Max ₪3,500. Up to 1 stop.
"""

import os, time, logging, requests
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

DESTINATIONS = [
    # איי יוון — עדיפות גבוהה
    {"code": "KGS", "name": "קוס"},
    {"code": "RHO", "name": "רודוס"},
    {"code": "CFU", "name": "קורפו"},
    {"code": "EFL", "name": "קפלוניה"},
    {"code": "PVK", "name": "לפקדה / פרבזה"},
    {"code": "ZTH", "name": "זקינתוס"},
    {"code": "SKG", "name": "סלוניקי"},
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
    {"code": "LIS", "name": "ליסבון"},
    {"code": "MAD", "name": "מדריד"},
    {"code": "WAW", "name": "ורשה"},
    {"code": "BER", "name": "ברלין"},
    {"code": "MUC", "name": "מינכן"},
    # מזה"ת ואסיה
    {"code": "DXB", "name": "דובאי"},
    {"code": "BKK", "name": "בנגקוק"},
    {"code": "SIN", "name": "סינגפור"},
    {"code": "CAI", "name": "קהיר"},
    # ארה"ב
    {"code": "JFK", "name": "ניו יורק"},
    {"code": "MIA", "name": "מיאמי"},
]

# Search window: 3 days → 6 months, weekly intervals
def search_dates():
    now   = datetime.utcnow()
    dates = []
    cur   = now + timedelta(days=3)
    end   = now + timedelta(days=183)
    while cur <= end:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=7 if (cur - now).days < 60 else 14)
    return dates

# Prague: July-August only
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


def deep_link(source, origin, dest, dep):
    try:
        dt = datetime.strptime(dep[:10], "%Y-%m-%d")
    except:
        dt = datetime.now()
    d8   = dt.strftime("%Y%m%d")
    dy   = dt.strftime("%Y-%m-%d")
    slug = KIWI_SLUGS.get(dest, dest.lower())
    m = {
        "Google Flights": f"https://www.google.com/travel/flights/search?q=flights+from+{origin}+to+{dest}+on+{dy}",
        "Aviasales":      f"https://www.aviasales.com/search/{origin}{d8}{dest}1",
        "Skyscanner":     f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8}/?adults=1&cabinclass=economy&stops=!twoPlusStops",
        "Kiwi.com":       f"https://www.kiwi.com/en/search/results/tel-aviv-israel/{slug}/{dy}/{dy}?stops=0&adults=1",
    }
    return m.get(source, m["Skyscanner"])


class GoogleFlightsScraper:
    """Primary source — SerpAPI Google Flights. Real-time verified prices."""
    URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "FlightScanner/2.0"})

    def search(self, origin, dest, dep_date):
        if not self.api_key:
            logger.warning("No SERPAPI_KEY — Google Flights disabled")
            return []
        try:
            r = self.session.get(self.URL, params={
                "engine":        "google_flights",
                "departure_id":  origin,
                "arrival_id":    dest,
                "outbound_date": dep_date,
                "travel_class":  1,   # Economy
                "stops":         2,   # 0=any, 1=nonstop, 2=up to 1 stop
                "currency":      "ILS",
                "hl":            "iw",
                "api_key":       self.api_key,
            }, timeout=20)

            if r.status_code == 429:
                logger.warning("SerpAPI quota exhausted")
                return []
            r.raise_for_status()
            data = r.json()

            if "error" in data:
                logger.warning(f"SerpAPI: {data['error']}")
                return []

            results = []
            all_flights = data.get("best_flights", []) + data.get("other_flights", [])

            for f in all_flights:
                price = f.get("price", 0)
                if not price or price <= 0:
                    continue
                legs  = f.get("flights", [])
                stops = len(legs) - 1
                if stops > 1:
                    continue
                dep = legs[0].get("departure_airport", {}).get("time", dep_date) if legs else dep_date
                arr = legs[-1].get("arrival_airport", {}).get("time", "") if legs else ""
                airline = legs[0].get("airline", "?") if legs else "?"
                results.append({
                    "source":           "Google Flights",
                    "origin":           origin,
                    "destination":      dest,
                    "price_ils":        int(price),
                    "price_usd":        round(price / ILS_PER_USD, 2),
                    "price_verified":   True,
                    "departure":        dep,
                    "arrival":          arr,
                    "return_departure": "",
                    "return_arrival":   "",
                    "duration_min":     f.get("total_duration", 0),
                    "stops":            stops,
                    "airline":          airline,
                    "deep_link":        deep_link("Google Flights", origin, dest, dep[:10]),
                })

            time.sleep(1.5 + random.uniform(0.2, 0.5))
            return results

        except Exception as e:
            logger.warning(f"[Google Flights] {origin}→{dest} {dep_date}: {e}")
            return []


class AviasalesScraper:
    """Secondary source — cached prices from Aviasales."""
    V1_URL = "https://api.travelpayouts.com/v1/prices/cheap"
    V3_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    def __init__(self):
        self.token = os.getenv("AVIASALES_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "FlightScanner/2.0"})

    def search(self, origin, dest, dep_date):
        results = self._v3(origin, dest, dep_date)
        if not results:
            results = self._v1(origin, dest, dep_date[:7])
        return results

    def _v3(self, origin, dest, dep_date):
        params = {
            "origin": origin, "destination": dest,
            "departure_at": dep_date, "sorting": "price",
            "direct": "false", "limit": 5,
            "currency": "usd", "market": "il",
        }
        if self.token:
            params["token"] = self.token
        try:
            r = self.session.get(self.V3_URL, params=params, timeout=12)
            r.raise_for_status()
            d = r.json()
            results = []
            for f in d.get("data", []):
                price = float(f.get("price", 0))
                if price <= 0: continue
                stops = f.get("transfers", 0)
                if stops > 1: continue
                dep = f.get("departure_at", dep_date + "T00:00:00")
                results.append({
                    "source": "Aviasales", "origin": origin, "destination": dest,
                    "price_ils": round(price * ILS_PER_USD),
                    "price_usd": price, "price_verified": True,
                    "departure": dep, "arrival": "",
                    "return_departure": f.get("return_at", ""), "return_arrival": "",
                    "duration_min": f.get("duration", 0), "stops": stops,
                    "airline": f.get("airline", "?"),
                    "deep_link": deep_link("Aviasales", origin, dest, dep[:10]),
                })
            time.sleep(1.0)
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
            flights = r.json().get("data", {}).get(dest, {})
            results = []
            for _, f in (flights.items() if isinstance(flights, dict) else []):
                price = float(f.get("price", 0))
                if price <= 0: continue
                stops = f.get("transfers", 0)
                if stops > 1: continue
                dep = f.get("departure_at", month + "-01T00:00:00")
                results.append({
                    "source": "Aviasales", "origin": origin, "destination": dest,
                    "price_ils": round(price * ILS_PER_USD),
                    "price_usd": price, "price_verified": True,
                    "departure": dep, "arrival": "",
                    "return_departure": "", "return_arrival": "",
                    "duration_min": f.get("duration", 0), "stops": stops,
                    "airline": f.get("airline", "?"),
                    "deep_link": deep_link("Aviasales", origin, dest, dep[:10]),
                })
            time.sleep(1.0)
            return results
        except Exception as e:
            logger.warning(f"[Aviasales v1] {origin}→{dest}: {e}")
            return []


def scan_destinations(dest_list):
    gf_scraper   = GoogleFlightsScraper()
    av_scraper   = AviasalesScraper()
    dates        = search_dates()
    dest_map     = {d["code"]: d["name"] for d in dest_list}
    all_results  = []

    logger.info(f"Scanning {len(dest_list)} destinations × {len(dates)} dates")
    logger.info(f"SerpAPI key: {'set ✅' if gf_scraper.api_key else 'missing ❌'}")
    logger.info(f"Search window: {dates[0]} → {dates[-1]}")

    for dest in dest_list:
        code = dest["code"]
        if code == "TLV":
            continue
        months_only = DEST_RULES.get(code, {}).get("months_only", [])
        dest_results = []

        for dep_date in dates:
            if months_only and int(dep_date[5:7]) not in months_only:
                continue

            # Google Flights first (real-time)
            gf_results = gf_scraper.search("TLV", code, dep_date)
            dest_results.extend(gf_results)

            # Aviasales as supplement (only call if Google returned nothing)
            if not gf_results:
                av_results = av_scraper.search("TLV", code, dep_date)
                dest_results.extend(av_results)

        for f in dest_results:
            f["dest_name"] = dest["name"]
            f.setdefault("window_label", f.get("departure", "")[:10])

        logger.info(f"  TLV→{code}: {len(dest_results)} results")
        all_results.extend(dest_results)

    logger.info(f"Total verified results: {len(all_results)}")
    return all_results


def scan_all_flights():
    logger.info("🛫 Full scan — real prices only")
    return scan_destinations(DESTINATIONS)


def scan_focused(query):
    q = query.strip().upper()
    matched = [d for d in DESTINATIONS
               if q in d["code"] or q in d["name"].upper()]
    if not matched:
        words = query.lower().split()
        matched = [d for d in DESTINATIONS if any(w in d["name"] for w in words)]
    if not matched:
        matched = DESTINATIONS
    return scan_destinations(matched)


def find_best_deals(flights, top_n=20):
    """Best verified deal per destination, sorted price low→high."""
    seen = {}
    for f in flights:
        if not f.get("price_verified"):
            continue
        price = f.get("price_ils", 99999)
        if price <= 0 or price > MAX_PRICE_ILS:
            continue
        if f.get("stops", 0) > 1:
            continue
        key = f["destination"]
        if key not in seen or price < seen[key]["price_ils"]:
            seen[key] = f
    deals = sorted(seen.values(), key=lambda x: x["price_ils"])
    logger.info(f"Best deals (≤₪{MAX_PRICE_ILS}): {len(deals)}")
    return deals[:top_n]
