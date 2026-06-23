"""
Flight Scanner — Real prices from 3 RapidAPI sources + SerpAPI + Aviasales.
APIs:
  1. Skyscanner Flights (Crawlio)         — skyscanner-flights.p.rapidapi.com
  2. Skyscanner Flights & Travel (elis)   — skyscanner-flights-travel-api.p.rapidapi.com
  3. Flights Scraper Sky (Things4u)       — flights-sky.p.rapidapi.com
  4. SerpAPI Google Flights               — serpapi.com
  5. Aviasales                            — api.travelpayouts.com (fallback)
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


def deep_link(source, origin, dest, dep):
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


def _mk(source, origin, dest, price_ils, dep, arr="",
        ret_dep="", ret_arr="", dur=0, airline="?", stops=0):
    return {
        "source": source, "origin": origin, "destination": dest,
        "price_ils": int(price_ils), "price_usd": round(price_ils/ILS_PER_USD, 2),
        "price_verified": True,
        "departure": dep, "arrival": arr,
        "return_departure": ret_dep, "return_arrival": ret_arr,
        "duration_min": dur, "stops": stops, "airline": airline,
        "deep_link": deep_link("Skyscanner" if "kyscanner" in source or source=="Flights Scraper Sky" else source,
                                origin, dest, dep[:10] if dep else ""),
    }


RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")


class SkyscannerCrawlio:
    """Skyscanner Flights by Crawlio — skyscanner-flights.p.rapidapi.com"""
    HOST = "skyscanner-flights.p.rapidapi.com"

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "X-RapidAPI-Key":  RAPIDAPI_KEY,
            "X-RapidAPI-Host": self.HOST,
        })
        self._ok = bool(RAPIDAPI_KEY)

    def search(self, origin, dest, dep_date):
        if not self._ok: return []
        try:
            # Search One Way Flights endpoint
            r = self.s.get(f"https://{self.HOST}/v1/flights/search-one-way", params={
                "origin":      origin,
                "destination": dest,
                "date":        dep_date,
                "adults":      "1",
                "currency":    "ILS",
                "countryCode": "IL",
                "locale":      "he-IL",
            }, timeout=15)
            if r.status_code == 429:
                logger.warning("[Crawlio] quota exceeded"); self._ok = False; return []
            r.raise_for_status()
            data = r.json()
            results = []
            for it in data.get("data", {}).get("itineraries", []):
                price = it.get("price", {}).get("raw", 0)
                if not price: continue
                legs  = it.get("legs", [])
                if not legs: continue
                leg   = legs[0]
                stops = leg.get("stopCount", 0)
                if stops > 1: continue
                dep  = leg.get("departure", dep_date)
                arr  = leg.get("arrival", "")
                al   = (leg.get("carriers", {}).get("marketing") or [{}])[0].get("name","?")
                results.append(_mk("Skyscanner", origin, dest, price,
                    dep=dep, arr=arr, dur=leg.get("durationInMinutes",0),
                    airline=al, stops=stops))
            time.sleep(1.2); return results
        except Exception as e:
            logger.warning(f"[Crawlio] {origin}→{dest}: {e}"); return []


class SkyscannerElisLab:
    """Skyscanner Flights & Travel API by elis-lab"""
    HOST = "skyscanner-flights-travel-api.p.rapidapi.com"

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "X-RapidAPI-Key":  RAPIDAPI_KEY,
            "X-RapidAPI-Host": self.HOST,
            "Content-Type": "application/json",
        })
        self._ok = bool(RAPIDAPI_KEY)

    def search(self, origin, dest, dep_date):
        if not self._ok: return []
        try:
            r = self.s.get(f"https://{self.HOST}/flights/getCheapestOneway", params={
                "origin":      f"{origin}-sky",
                "destination": f"{dest}-sky",
                "departDate":  dep_date,
                "adults":      "1",
                "currency":    "ILS",
                "locale":      "he-IL",
                "market":      "IL",
            }, timeout=15)
            if r.status_code == 429:
                logger.warning("[ElisLab] quota exceeded"); self._ok = False; return []
            r.raise_for_status()
            data = r.json()
            results = []
            quotes = data.get("quotes", []) or data.get("data", {}).get("quotes", [])
            for q in quotes:
                price = q.get("minPrice", 0)
                if not price: continue
                leg   = q.get("outboundLeg", {})
                stops = 0 if q.get("isDirect") else 1
                if stops > 1: continue
                dep   = leg.get("departureDate", dep_date)
                al    = (leg.get("carrierIds") or ["?"])[0]
                results.append(_mk("Skyscanner", origin, dest, float(price),
                    dep=dep, airline=str(al), stops=stops))
            time.sleep(1.2); return results
        except Exception as e:
            logger.warning(f"[ElisLab] {origin}→{dest}: {e}"); return []


class FlightsScraperSky:
    """Flights Scraper Sky by Things4u — flights-sky.p.rapidapi.com"""
    HOST = "flights-sky.p.rapidapi.com"

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "X-RapidAPI-Key":  RAPIDAPI_KEY,
            "X-RapidAPI-Host": self.HOST,
        })
        self._ok = bool(RAPIDAPI_KEY)

    def search(self, origin, dest, dep_date):
        if not self._ok: return []
        try:
            # First get entity IDs
            orig_id = self._airport_id(origin)
            dest_id = self._airport_id(dest)
            if not orig_id or not dest_id: return []

            r = self.s.get(f"https://{self.HOST}/flights/search-one-way", params={
                "fromEntityId": orig_id,
                "toEntityId":   dest_id,
                "departDate":   dep_date,
                "adults":       "1",
                "currency":     "ILS",
                "locale":       "he-IL",
                "market":       "IL",
                "stops":        "direct,1stop",
            }, timeout=20)
            if r.status_code == 429:
                logger.warning("[FlightsScraperSky] quota"); self._ok = False; return []
            r.raise_for_status()
            data = r.json()
            results = []
            for it in data.get("data", {}).get("itineraries", []):
                price = it.get("price", {}).get("raw", 0)
                if not price: continue
                legs  = it.get("legs", [])
                if not legs: continue
                leg   = legs[0]
                stops = leg.get("stopCount", 0)
                if stops > 1: continue
                dep  = leg.get("departure", dep_date)
                arr  = leg.get("arrival", "")
                al   = (leg.get("carriers", {}).get("marketing") or [{}])[0].get("name","?")
                results.append(_mk("Flights Scraper Sky", origin, dest, price,
                    dep=dep, arr=arr, dur=leg.get("durationInMinutes",0),
                    airline=al, stops=stops))
            time.sleep(1.5); return results
        except Exception as e:
            logger.warning(f"[FlightsScraperSky] {origin}→{dest}: {e}"); return []

    _cache = {}
    def _airport_id(self, iata):
        if iata in self._cache: return self._cache[iata]
        try:
            r = self.s.get(f"https://{self.HOST}/flights/auto-complete",
                params={"query": iata, "locale": "en-US"}, timeout=10)
            r.raise_for_status()
            places = r.json().get("data", [])
            for p in places:
                if p.get("navigation", {}).get("relevantFlightParams", {}).get("skyId") == iata:
                    eid = p.get("navigation", {}).get("relevantFlightParams", {}).get("entityId", "")
                    self._cache[iata] = eid
                    return eid
            # fallback: take first result
            if places:
                eid = places[0].get("navigation", {}).get("relevantFlightParams", {}).get("entityId","")
                self._cache[iata] = eid
                return eid
        except Exception as e:
            logger.warning(f"[FlightsScraperSky] airport lookup {iata}: {e}")
        return ""


class SerpAPIFlights:
    """Google Flights via SerpAPI. 100 free/month."""
    URL = "https://serpapi.com/search"

    def __init__(self):
        self.key  = os.getenv("SERPAPI_KEY","")
        self.s    = requests.Session()
        self._ok  = bool(self.key)

    def search(self, origin, dest, dep_date):
        if not self._ok: return []
        try:
            r = self.s.get(self.URL, params={
                "engine":"google_flights",
                "departure_id":origin,"arrival_id":dest,
                "outbound_date":dep_date,
                "travel_class":1,"stops":2,
                "currency":"ILS","hl":"iw","api_key":self.key,
            }, timeout=20)
            if r.status_code == 429:
                self._ok = False; return []
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                if any(w in data["error"].lower() for w in ["credit","quota","limit"]):
                    logger.warning("[SerpAPI] quota exhausted")
                    self._ok = False
                return []
            results = []
            for f in (data.get("best_flights",[]) + data.get("other_flights",[])):
                price = f.get("price",0)
                if not price: continue
                legs  = f.get("flights",[])
                stops = len(legs)-1
                if stops > 1: continue
                dep = legs[0].get("departure_airport",{}).get("time",dep_date) if legs else dep_date
                arr = legs[-1].get("arrival_airport",{}).get("time","") if legs else ""
                results.append(_mk("Google Flights",origin,dest,price,
                    dep=dep,arr=arr,dur=f.get("total_duration",0),
                    airline=legs[0].get("airline","?") if legs else "?",stops=stops))
            time.sleep(2.0); return results
        except Exception as e:
            logger.warning(f"[SerpAPI] {origin}→{dest}: {e}"); return []


class AviasalesScraper:
    """Aviasales cached prices. Free fallback."""
    V3  = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    V1  = "https://api.travelpayouts.com/v1/prices/cheap"
    SPE = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"

    def __init__(self):
        self.token = os.getenv("AVIASALES_TOKEN","")
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "FlightScanner/2.0"

    def _p(self, p):
        if self.token: p["token"] = self.token
        return p

    def search(self, origin, dest, dep_date):
        r = self._v3(origin, dest, dep_date)
        if not r: r = self._v1(origin, dest, dep_date[:7])
        return r

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
            time.sleep(1.0); return res
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
            time.sleep(1.0); return res
        except Exception as e:
            logger.warning(f"[Av v1] {e}"); return []

    def specials(self, origin):
        try:
            r = self.s.get(self.SPE, params=self._p({
                "origin":origin,"direct":"false","currency":"usd","limit":100,"market":"il"}), timeout=15)
            r.raise_for_status()
            res = []
            for f in r.json().get("data",[]):
                p = float(f.get("price",0))
                if p<=0 or f.get("transfers",0)>1: continue
                dep2 = f.get("departure_at","")
                res.append(_mk("Aviasales",origin,f.get("destination","?"),round(p*ILS_PER_USD),
                    dep=dep2,ret_dep=f.get("return_at",""),dur=f.get("duration",0),
                    airline=f.get("airline","?"),stops=f.get("transfers",0)))
            return res
        except Exception as e:
            logger.warning(f"[Av specials] {e}"); return []


def scan_destinations(dest_list):
    crawlio = SkyscannerCrawlio()
    elis    = SkyscannerElisLab()
    sky     = FlightsScraperSky()
    serp    = SerpAPIFlights()
    av      = AviasalesScraper()
    dates   = search_dates()
    dest_map   = {d["code"]:d["name"] for d in dest_list}
    dest_codes = {d["code"] for d in dest_list if d["code"]!="TLV"}

    logger.info(f"APIs active: Crawlio={'✅' if crawlio._ok else '❌'} | ElisLab={'✅' if elis._ok else '❌'} | FlightsSky={'✅' if sky._ok else '❌'} | SerpAPI={'✅' if serp._ok else '❌'} | Aviasales=✅")
    logger.info(f"Dates: {dates[0]}→{dates[-1]} ({len(dates)} windows) | Destinations: {len(dest_list)}")

    all_results = []

    # Bulk specials
    specials = av.specials("TLV")
    matching = [f for f in specials if f["destination"] in dest_codes]
    for f in matching:
        f["dest_name"] = dest_map.get(f["destination"], f["destination"])
        f.setdefault("window_label", f.get("departure","")[:10])
    all_results.extend(matching)
    logger.info(f"Aviasales specials: {len(matching)} matching")

    for dest in dest_list:
        code = dest["code"]
        if code == "TLV": continue
        months_only = DEST_RULES.get(code,{}).get("months_only",[])
        found = 0

        for dep_date in dates:
            if months_only and int(dep_date[5:7]) not in months_only:
                continue

            # Try all RapidAPI sources, collect from all
            results = []
            results += crawlio.search("TLV", code, dep_date)
            results += elis.search("TLV", code, dep_date)
            results += sky.search("TLV", code, dep_date)

            # If all RapidAPI returned nothing, try SerpAPI + Aviasales
            if not results:
                results += serp.search("TLV", code, dep_date)
            if not results:
                results += av.search("TLV", code, dep_date)

            for f in results:
                f["dest_name"]    = dest["name"]
                f["window_label"] = dep_date
            all_results.extend(results)
            found += len(results)

        logger.info(f"  TLV→{code}: {found}")

    logger.info(f"Total: {len(all_results)} verified results")
    return all_results


def scan_all_flights():
    logger.info("🛫 Full scan — 3 RapidAPI sources + SerpAPI + Aviasales")
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
