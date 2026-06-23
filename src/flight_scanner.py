"""
Flight Scanner — Real prices via multiple APIs.
Primary: Skyscanner via RapidAPI (500 free/month) 
         + SerpAPI Google Flights (100 free/month)
Fallback: Aviasales v1/v3 (free, cached prices)
"""

import os, time, logging, requests
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

DESTINATIONS = [
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
    {"code": "BER", "name": "ברלין"},
    {"code": "DXB", "name": "דובאי"},
    {"code": "BKK", "name": "בנגקוק"},
    {"code": "CAI", "name": "קהיר"},
    {"code": "JFK", "name": "ניו יורק"},
]

DEST_RULES    = {"PRG": {"months_only": [7, 8]}}
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
    "AMS":"amsterdam-netherlands","DXB":"dubai-united-arab-emirates",
    "BKK":"bangkok-thailand","JFK":"new-york-united-states","MAD":"madrid-spain",
}


def dl(source, origin, dest, dep):
    try: dt = datetime.strptime(dep[:10], "%Y-%m-%d")
    except: dt = datetime.now()
    d8   = dt.strftime("%Y%m%d")
    dy   = dt.strftime("%Y-%m-%d")
    slug = KIWI_SLUGS.get(dest, dest.lower())
    m = {
        "Skyscanner":     f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8}/?adults=1&cabinclass=economy&stops=!twoPlusStops",
        "Google Flights": f"https://www.google.com/travel/flights/search?q=flights+from+{origin}+to+{dest}+on+{dy}",
        "Aviasales":      f"https://www.aviasales.com/search/{origin}{d8}{dest}1",
        "Kiwi.com":       f"https://www.kiwi.com/en/search/results/tel-aviv-israel/{slug}/{dy}/{dy}?stops=0&adults=1",
    }
    return m.get(source, m["Skyscanner"])


def search_dates():
    now = datetime.utcnow()
    dates, cur = [], now + timedelta(days=3)
    end = now + timedelta(days=183)
    while cur <= end:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=7 if (cur-now).days < 60 else 14)
    return dates


def _make(source, origin, dest, price_ils, dep, arr="",
          ret_dep="", ret_arr="", dur=0, airline="?", stops=0):
    return {
        "source": source, "origin": origin, "destination": dest,
        "price_ils": int(price_ils), "price_usd": round(price_ils/ILS_PER_USD, 2),
        "price_verified": True,
        "departure": dep, "arrival": arr,
        "return_departure": ret_dep, "return_arrival": ret_arr,
        "duration_min": dur, "stops": stops, "airline": airline,
        "deep_link": dl(source, origin, dest, dep[:10] if dep else ""),
    }


class SkyscannerRapidScraper:
    """Skyscanner via RapidAPI — 500 free calls/month. Real-time prices."""
    URL = "https://skyscanner50.p.rapidapi.com/api/v1/searchFlights"

    def __init__(self):
        self.key = os.getenv("RAPIDAPI_KEY", "")
        self.session = requests.Session()

    def search(self, origin, dest, dep_date):
        if not self.key:
            return []
        try:
            r = self.session.get(self.URL, headers={
                "X-RapidAPI-Key": self.key,
                "X-RapidAPI-Host": "skyscanner50.p.rapidapi.com",
            }, params={
                "fromId": f"{origin}-sky",
                "toId":   f"{dest}-sky",
                "departDate": dep_date,
                "adults": "1",
                "currency": "ILS",
                "countryCode": "IL",
                "market": "il-IL",
                "locale": "he-IL",
            }, timeout=15)
            if r.status_code == 429:
                logger.warning("[Skyscanner RapidAPI] quota exceeded")
                return []
            r.raise_for_status()
            data = r.json()
            results = []
            for itinerary in data.get("data", {}).get("itineraries", []):
                price = itinerary.get("price", {}).get("raw", 0)
                if not price: continue
                legs = itinerary.get("legs", [])
                if not legs: continue
                leg = legs[0]
                stops = leg.get("stopCount", 0)
                if stops > 1: continue
                dep = leg.get("departure", dep_date)
                arr = leg.get("arrival", "")
                airline = leg.get("carriers", {}).get("marketing", [{}])[0].get("name", "?")
                results.append(_make("Skyscanner", origin, dest, price,
                    dep=dep, arr=arr, dur=leg.get("durationInMinutes",0),
                    airline=airline, stops=stops))
            time.sleep(1.0 + random.uniform(0.2, 0.4))
            return results
        except Exception as e:
            logger.warning(f"[Skyscanner RapidAPI] {origin}→{dest}: {e}")
            return []


class SerpAPIGoogleFlights:
    """Google Flights via SerpAPI. 100 free/month."""
    URL = "https://serpapi.com/search"

    def __init__(self):
        self.key = os.getenv("SERPAPI_KEY", "")
        self.session = requests.Session()
        self._quota_ok = True

    def search(self, origin, dest, dep_date):
        if not self.key or not self._quota_ok:
            return []
        try:
            r = self.session.get(self.URL, params={
                "engine": "google_flights",
                "departure_id": origin, "arrival_id": dest,
                "outbound_date": dep_date,
                "travel_class": 1, "stops": 2,
                "currency": "ILS", "hl": "iw", "api_key": self.key,
            }, timeout=20)
            if r.status_code == 429:
                logger.warning("[SerpAPI] quota exhausted — disabling for this run")
                self._quota_ok = False
                return []
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                if "credit" in data["error"].lower() or "quota" in data["error"].lower():
                    self._quota_ok = False
                logger.warning(f"[SerpAPI] {data['error']}")
                return []
            results = []
            for f in (data.get("best_flights",[]) + data.get("other_flights",[])):
                price = f.get("price", 0)
                if not price: continue
                legs  = f.get("flights", [])
                stops = len(legs) - 1
                if stops > 1: continue
                dep = legs[0].get("departure_airport",{}).get("time", dep_date) if legs else dep_date
                arr = legs[-1].get("arrival_airport",{}).get("time","") if legs else ""
                results.append(_make("Google Flights", origin, dest, price,
                    dep=dep, arr=arr,
                    dur=f.get("total_duration",0),
                    airline=legs[0].get("airline","?") if legs else "?",
                    stops=stops))
            time.sleep(2.0 + random.uniform(0.2, 0.5))
            return results
        except Exception as e:
            logger.warning(f"[SerpAPI] {origin}→{dest}: {e}")
            return []


class AviasalesScraper:
    """Aviasales cached prices. Free, no auth."""
    V3  = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    V1  = "https://api.travelpayouts.com/v1/prices/cheap"
    SPE = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"

    def __init__(self):
        self.token = os.getenv("AVIASALES_TOKEN","")
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "FlightScanner/2.0"

    def _tok(self, p):
        if self.token: p["token"] = self.token
        return p

    def search(self, origin, dest, dep_date):
        r = self._v3(origin, dest, dep_date)
        if not r: r = self._v1(origin, dest, dep_date[:7])
        return r

    def _v3(self, origin, dest, dep_date):
        try:
            r = self.s.get(self.V3, params=self._tok({
                "origin":origin,"destination":dest,"departure_at":dep_date,
                "sorting":"price","direct":"false","limit":5,"currency":"usd","market":"il"}), timeout=12)
            r.raise_for_status()
            results = []
            for f in r.json().get("data",[]):
                p = float(f.get("price",0))
                if p<=0 or f.get("transfers",0)>1: continue
                dep = f.get("departure_at", dep_date+"T00:00:00")
                results.append(_make("Aviasales",origin,dest,round(p*ILS_PER_USD),
                    dep=dep,ret_dep=f.get("return_at",""),
                    dur=f.get("duration",0),airline=f.get("airline","?"),
                    stops=f.get("transfers",0)))
            time.sleep(1.0); return results
        except Exception as e:
            logger.warning(f"[Aviasales v3] {e}"); return []

    def _v1(self, origin, dest, month):
        try:
            r = self.s.get(self.V1, params=self._tok({
                "origin":origin,"destination":dest,"depart_date":month,
                "currency":"usd","page":1}), timeout=12)
            r.raise_for_status()
            flights = r.json().get("data",{}).get(dest,{})
            results = []
            for _,f in (flights.items() if isinstance(flights,dict) else []):
                p = float(f.get("price",0))
                if p<=0 or f.get("transfers",0)>1: continue
                dep = f.get("departure_at", month+"-01T00:00:00")
                results.append(_make("Aviasales",origin,dest,round(p*ILS_PER_USD),
                    dep=dep,dur=f.get("duration",0),
                    airline=f.get("airline","?"),stops=f.get("transfers",0)))
            time.sleep(1.0); return results
        except Exception as e:
            logger.warning(f"[Aviasales v1] {e}"); return []

    def specials(self, origin):
        try:
            r = self.s.get(self.SPE, params=self._tok({
                "origin":origin,"direct":"false","currency":"usd","limit":100,"market":"il"}), timeout=15)
            r.raise_for_status()
            results = []
            for f in r.json().get("data",[]):
                p = float(f.get("price",0))
                if p<=0 or f.get("transfers",0)>1: continue
                dep = f.get("departure_at","")
                results.append(_make("Aviasales",origin,f.get("destination","?"),round(p*ILS_PER_USD),
                    dep=dep,ret_dep=f.get("return_at",""),
                    dur=f.get("duration",0),airline=f.get("airline","?"),
                    stops=f.get("transfers",0)))
            return results
        except Exception as e:
            logger.warning(f"[Aviasales specials] {e}"); return []


def scan_destinations(dest_list):
    gf  = SerpAPIGoogleFlights()
    sky = SkyscannerRapidScraper()
    av  = AviasalesScraper()
    dates = search_dates()
    dest_map   = {d["code"]:d["name"] for d in dest_list}
    dest_codes = {d["code"] for d in dest_list if d["code"]!="TLV"}

    logger.info(f"APIs: SerpAPI={'✅' if gf.key else '❌'} | RapidAPI={'✅' if sky.key else '❌'} | Aviasales=✅")
    logger.info(f"Dates: {dates[0]} → {dates[-1]} ({len(dates)} windows)")

    all_results = []

    # Bulk specials from Aviasales
    specials = av.specials("TLV")
    for f in specials:
        if f["destination"] in dest_codes:
            f["dest_name"] = dest_map.get(f["destination"], f["destination"])
            f.setdefault("window_label", f.get("departure","")[:10])
            all_results.append(f)
    logger.info(f"Aviasales specials: {len([f for f in specials if f['destination'] in dest_codes])} matching")

    # Per destination
    for dest in dest_list:
        code = dest["code"]
        if code == "TLV": continue
        months_only = DEST_RULES.get(code,{}).get("months_only",[])
        found = 0

        for dep_date in dates:
            if months_only and int(dep_date[5:7]) not in months_only:
                continue

            # Try in priority order
            results = sky.search("TLV", code, dep_date)   # Skyscanner RapidAPI
            if not results:
                results = gf.search("TLV", code, dep_date)   # Google Flights SerpAPI
            if not results:
                results = av.search("TLV", code, dep_date)   # Aviasales fallback

            for f in results:
                f["dest_name"]    = dest["name"]
                f["window_label"] = dep_date
            all_results.extend(results)
            found += len(results)

        logger.info(f"  TLV→{code}: {found} results")

    logger.info(f"Total verified: {len(all_results)}")
    return all_results


def scan_all_flights():
    logger.info("🛫 Full scan — real prices only")
    return scan_destinations(DESTINATIONS)


def scan_focused(query):
    q = query.strip().upper()
    matched = [d for d in DESTINATIONS if q in d["code"] or q in d["name"].upper()]
    if not matched:
        words = query.lower().split()
        matched = [d for d in DESTINATIONS if any(w in d["name"] for w in words)]
    return scan_destinations(matched or DESTINATIONS)


def find_best_deals(flights, top_n=20):
    seen = {}
    for f in flights:
        if not f.get("price_verified"): continue
        price = f.get("price_ils", 99999)
        if price<=0 or price>MAX_PRICE_ILS or f.get("stops",0)>1: continue
        key = f["destination"]
        if key not in seen or price < seen[key]["price_ils"]:
            seen[key] = f
    deals = sorted(seen.values(), key=lambda x: x["price_ils"])
    logger.info(f"Best deals ≤₪{MAX_PRICE_ILS}: {len(deals)}")
    return deals[:top_n]
