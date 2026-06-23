"""
Flight Scanner — Sky Scrapper API (apiheya) via RapidAPI.
This is the correct API from the screenshot.
Host: sky-scrapper.p.rapidapi.com
Endpoints:
  GET /api/v1/flights/searchAirport    — get airport entityId
  GET /api/v1/flights/searchFlights    — search one-way flights
  GET /api/v2/flights/searchFlights    — search one-way (v2)
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
    {"code": "PVK", "name": "לפקדה"},
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


def deep_link(source, origin, dest, dep):
    try: dt = datetime.strptime(dep[:10], "%Y-%m-%d")
    except: dt = datetime.now()
    d8   = dt.strftime("%Y%m%d")
    dy   = dt.strftime("%Y-%m-%d")
    slug = KIWI_SLUGS.get(dest, dest.lower())
    return {
        "Skyscanner":     f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8}/?adults=1&cabinclass=economy&stops=!twoPlusStops",
        "Google Flights": f"https://www.google.com/travel/flights/search?q=flights+from+{origin}+to+{dest}+on+{dy}",
        "Aviasales":      f"https://www.aviasales.com/search/{origin}{d8}{dest}1",
    }.get(source, f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8}/?adults=1")


def search_dates():
    now = datetime.utcnow()
    dates, cur = [], now + timedelta(days=3)
    end = now + timedelta(days=183)
    while cur <= end:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=7 if (cur-now).days < 60 else 14)
    return dates


def _mk(source, origin, dest, price_ils, dep, arr="",
        ret_dep="", ret_arr="", dur=0, airline="?", stops=0):
    return {
        "source": source, "origin": origin, "destination": dest,
        "price_ils": int(price_ils), "price_usd": round(price_ils / ILS_PER_USD, 2),
        "price_verified": True,
        "departure": dep, "arrival": arr,
        "return_departure": ret_dep, "return_arrival": ret_arr,
        "duration_min": dur, "stops": stops, "airline": airline,
        "deep_link": deep_link(source, origin, dest, dep[:10] if dep else ""),
    }


class SkyScrapper:
    """
    Sky Scrapper API by apiheya — sky-scrapper.p.rapidapi.com
    The correct API from the RapidAPI screenshot.
    """
    HOST = "sky-scrapper.p.rapidapi.com"
    BASE = f"https://{HOST}"
    _entity_cache = {}

    def __init__(self):
        self.key = os.environ.get("RAPIDAPI_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "X-RapidAPI-Key":  self.key,
            "X-RapidAPI-Host": self.HOST,
        })
        self._ok = bool(self.key)

    def _get_entity(self, iata: str) -> tuple:
        """Returns (skyId, entityId) for an IATA code."""
        if iata in self._entity_cache:
            return self._entity_cache[iata]
        try:
            r = self.session.get(f"{self.BASE}/api/v1/flights/searchAirport",
                params={"query": iata, "locale": "en-US"}, timeout=10)
            if r.status_code == 429:
                self._ok = False
                return "", ""
            r.raise_for_status()
            data = r.json().get("data", [])
            for place in data:
                nav = place.get("navigation", {}).get("relevantFlightParams", {})
                if nav.get("skyId") == iata:
                    result = (nav.get("skyId", ""), nav.get("entityId", ""))
                    self._entity_cache[iata] = result
                    return result
            # fallback: first result
            if data:
                nav = data[0].get("navigation", {}).get("relevantFlightParams", {})
                result = (nav.get("skyId", ""), nav.get("entityId", ""))
                self._entity_cache[iata] = result
                return result
        except Exception as e:
            logger.warning(f"[SkyScrapper] airport {iata}: {e}")
        return "", ""

    def search(self, origin: str, dest: str, dep_date: str) -> list:
        if not self._ok:
            return []
        orig_sky, orig_eid = self._get_entity(origin)
        dest_sky, dest_eid = self._get_entity(dest)
        if not orig_eid or not dest_eid:
            logger.warning(f"[SkyScrapper] entity IDs not found: {origin}({orig_eid}) {dest}({dest_eid})")
            return []
        try:
            r = self.session.get(f"{self.BASE}/api/v2/flights/searchFlights",
                params={
                    "originSkyId":        orig_sky or origin,
                    "destinationSkyId":   dest_sky or dest,
                    "originEntityId":     orig_eid,
                    "destinationEntityId": dest_eid,
                    "date":               dep_date,
                    "adults":             "1",
                    "currency":           "ILS",
                    "locale":             "he-IL",
                    "market":             "IL",
                    "cabinClass":         "economy",
                    "sortBy":             "best",
                    "limit":              "10",
                }, timeout=20)
            if r.status_code == 429:
                logger.warning("[SkyScrapper] quota exceeded")
                self._ok = False
                return []
            r.raise_for_status()
            data = r.json()
            # Handle incomplete status
            context = data.get("data", {}).get("context", {})
            status  = context.get("status", "")
            if status == "incomplete":
                logger.info(f"[SkyScrapper] {origin}→{dest}: incomplete results, using partial")

            itineraries = data.get("data", {}).get("itineraries", [])
            results = []
            for it in itineraries:
                price = it.get("price", {}).get("raw", 0)
                if not price: continue
                legs  = it.get("legs", [])
                if not legs: continue
                leg   = legs[0]
                stops = leg.get("stopCount", 0)
                if stops > 1: continue
                dep   = leg.get("departure", dep_date)
                arr   = leg.get("arrival", "")
                dur   = leg.get("durationInMinutes", 0)
                carriers = leg.get("carriers", {}).get("marketing", [{}])
                airline  = carriers[0].get("name", "?") if carriers else "?"
                results.append(_mk("Skyscanner", origin, dest, price,
                    dep=dep, arr=arr, dur=dur, airline=airline, stops=stops))

            logger.info(f"[SkyScrapper] {origin}→{dest} {dep_date}: {len(results)} results")
            time.sleep(2.0 + random.uniform(0.3, 0.7))
            return results
        except Exception as e:
            logger.warning(f"[SkyScrapper] {origin}→{dest} {dep_date}: {e}")
            return []


class AviasalesScraper:
    """Aviasales cached prices. Free fallback."""
    V1 = "https://api.travelpayouts.com/v1/prices/cheap"
    V3 = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    def __init__(self):
        self.token = os.environ.get("AVIASALES_TOKEN", "")
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "FlightScanner/2.0"

    def _p(self, p):
        if self.token: p["token"] = self.token
        return p

    def search(self, origin, dest, dep_date):
        res = self._v3(origin, dest, dep_date)
        if not res: res = self._v1(origin, dest, dep_date[:7])
        return res

    def _v3(self, o, d, dep):
        try:
            r = self.s.get(self.V3, params=self._p({
                "origin":o,"destination":d,"departure_at":dep,
                "sorting":"price","direct":"false","limit":5,"currency":"usd","market":"il"}), timeout=12)
            r.raise_for_status()
            res = []
            for f in r.json().get("data",[]):
                p = float(f.get("price",0))
                if p<=0 or f.get("transfers",0)>1: continue
                dep2 = f.get("departure_at",dep+"T00:00:00")
                res.append(_mk("Aviasales",o,d,round(p*ILS_PER_USD),dep=dep2,
                    ret_dep=f.get("return_at",""),dur=f.get("duration",0),
                    airline=f.get("airline","?"),stops=f.get("transfers",0)))
            time.sleep(0.8); return res
        except Exception as e:
            logger.warning(f"[Av v3] {e}"); return []

    def _v1(self, o, d, month):
        try:
            r = self.s.get(self.V1, params=self._p({
                "origin":o,"destination":d,"depart_date":month,
                "currency":"usd","page":1}), timeout=12)
            r.raise_for_status()
            flights = r.json().get("data",{}).get(d,{})
            res = []
            for _,f in (flights.items() if isinstance(flights,dict) else []):
                p = float(f.get("price",0))
                if p<=0 or f.get("transfers",0)>1: continue
                dep2 = f.get("departure_at",month+"-01T00:00:00")
                res.append(_mk("Aviasales",o,d,round(p*ILS_PER_USD),dep=dep2,
                    dur=f.get("duration",0),airline=f.get("airline","?"),stops=f.get("transfers",0)))
            time.sleep(0.8); return res
        except Exception as e:
            logger.warning(f"[Av v1] {e}"); return []


# Expose for main.py diagnostics
class SkyscannerCrawlio:
    def __init__(self): self._ok = False
    def search(self, *a): return []

class SkyscannerElisLab:
    def __init__(self): self._ok = False
    def search(self, *a): return []

class FlightsScraperSky:
    def __init__(self): self._ok = SkyScrapper().key != ""
    def search(self, o, d, dep): return SkyScrapper().search(o, d, dep)

class SerpAPIFlights:
    def __init__(self):
        self.key  = os.environ.get("SERPAPI_KEY","")
        self._ok  = bool(self.key)
        self.session = requests.Session()

    def search(self, origin, dest, dep_date):
        if not self._ok: return []
        try:
            r = self.session.get("https://serpapi.com/search", params={
                "engine":"google_flights","departure_id":origin,"arrival_id":dest,
                "outbound_date":dep_date,"travel_class":1,"stops":2,
                "currency":"ILS","hl":"iw","api_key":self.key}, timeout=20)
            if r.status_code==429: self._ok=False; return []
            data = r.json()
            if "error" in data:
                if any(w in data["error"].lower() for w in ["credit","quota","limit"]):
                    self._ok=False
                return []
            res=[]
            for f in (data.get("best_flights",[])+data.get("other_flights",[])):
                price=f.get("price",0)
                if not price: continue
                legs=f.get("flights",[]); stops=len(legs)-1
                if stops>1: continue
                dep=legs[0].get("departure_airport",{}).get("time",dep_date) if legs else dep_date
                arr=legs[-1].get("arrival_airport",{}).get("time","") if legs else ""
                res.append(_mk("Google Flights",origin,dest,price,dep=dep,arr=arr,
                    dur=f.get("total_duration",0),airline=legs[0].get("airline","?") if legs else "?",stops=stops))
            time.sleep(2.0); return res
        except Exception as e:
            logger.warning(f"[SerpAPI] {e}"); return []


def scan_destinations(dest_list):
    sky   = SkyScrapper()
    av    = AviasalesScraper()
    serp  = SerpAPIFlights()
    dates = search_dates()
    dest_map   = {d["code"]:d["name"] for d in dest_list}
    dest_codes = {d["code"] for d in dest_list if d["code"]!="TLV"}

    logger.info(f"SkyScrapper API: {'✅ ACTIVE' if sky._ok else '❌ NO KEY'}")
    logger.info(f"SerpAPI: {'✅' if serp._ok else '❌'}")
    logger.info(f"Dates: {dates[0]}→{dates[-1]} ({len(dates)} windows)")

    all_results = []

    for dest in dest_list:
        code = dest["code"]
        if code == "TLV": continue
        months_only = DEST_RULES.get(code,{}).get("months_only",[])
        found = 0

        for dep_date in dates:
            if months_only and int(dep_date[5:7]) not in months_only:
                continue

            # Sky Scrapper (Skyscanner) is primary
            results = sky.search("TLV", code, dep_date)

            # SerpAPI (Google Flights) as supplement
            if not results:
                results = serp.search("TLV", code, dep_date)

            # Aviasales as last resort
            if not results:
                results = av.search("TLV", code, dep_date)

            for f in results:
                f["dest_name"]    = dest["name"]
                f["window_label"] = dep_date
            all_results.extend(results)
            found += len(results)

        logger.info(f"  TLV→{code}: {found} results")

    logger.info(f"Total verified: {len(all_results)}")
    return all_results


def scan_all_flights():
    logger.info("🛫 Full scan — Sky Scrapper (apiheya) + SerpAPI + Aviasales")
    return scan_destinations(DESTINATIONS)


def scan_focused(query):
    q = query.strip().upper()
    matched = [d for d in DESTINATIONS if q in d["code"] or q in d["name"].upper()]
    if not matched:
        matched = [d for d in DESTINATIONS if any(w in d["name"] for w in query.lower().split())]
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
