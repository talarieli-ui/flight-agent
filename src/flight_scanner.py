"""
Flight Scanner v5 — Direct airline APIs for real prices.
Strategy: hit Wizz Air and Ryanair APIs directly (they're public, no auth).
These are the cheapest carriers on TLV→Europe routes.
Plus Aviasales as supplement, and search hub for everything else.
"""

import os, logging, requests, time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DESTINATIONS = [
    {"code": "KGS", "name": "קוס",            "flag": "🇬🇷", "category": "greek"},
    {"code": "RHO", "name": "רודוס",          "flag": "🇬🇷", "category": "greek"},
    {"code": "CFU", "name": "קורפו",          "flag": "🇬🇷", "category": "greek"},
    {"code": "EFL", "name": "קפלוניה",        "flag": "🇬🇷", "category": "greek"},
    {"code": "PVK", "name": "לפקדה / פרבזה",   "flag": "🇬🇷", "category": "greek"},
    {"code": "ZTH", "name": "זקינתוס",        "flag": "🇬🇷", "category": "greek"},
    {"code": "SKG", "name": "סלוניקי",        "flag": "🇬🇷", "category": "greek"},
    {"code": "JTR", "name": "סנטוריני",       "flag": "🇬🇷", "category": "greek"},
    {"code": "JMK", "name": "מיקונוס",        "flag": "🇬🇷", "category": "greek"},
    {"code": "HER", "name": "כרתים (הרקליון)", "flag": "🇬🇷", "category": "greek"},
    {"code": "CHQ", "name": "כרתים (חניה)",   "flag": "🇬🇷", "category": "greek"},
    {"code": "JSI", "name": "סקיאתוס",        "flag": "🇬🇷", "category": "greek"},
    {"code": "SMI", "name": "סמוס",           "flag": "🇬🇷", "category": "greek"},
    {"code": "ATH", "name": "אתונה",          "flag": "🇬🇷", "category": "greek"},
    {"code": "LHR", "name": "לונדון",         "flag": "🇬🇧", "category": "europe"},
    {"code": "CDG", "name": "פריז",           "flag": "🇫🇷", "category": "europe"},
    {"code": "FCO", "name": "רומא",           "flag": "🇮🇹", "category": "europe"},
    {"code": "BCN", "name": "ברצלונה",        "flag": "🇪🇸", "category": "europe"},
    {"code": "AMS", "name": "אמסטרדם",        "flag": "🇳🇱", "category": "europe"},
    {"code": "VIE", "name": "וינה",           "flag": "🇦🇹", "category": "europe"},
    {"code": "PRG", "name": "פראג",           "flag": "🇨🇿", "category": "europe"},
    {"code": "BUD", "name": "בודפשט",         "flag": "🇭🇺", "category": "europe"},
    {"code": "BER", "name": "ברלין",          "flag": "🇩🇪", "category": "europe"},
    {"code": "DXB", "name": "דובאי",          "flag": "🇦🇪", "category": "asia"},
    {"code": "BKK", "name": "בנגקוק",         "flag": "🇹🇭", "category": "asia"},
    {"code": "JFK", "name": "ניו יורק",       "flag": "🇺🇸", "category": "usa"},
]

DEST_RULES    = {"PRG": {"months_only": [7, 8]}}
ILS_PER_USD   = 3.7
EUR_PER_USD   = 0.92
ILS_PER_EUR   = ILS_PER_USD / EUR_PER_USD   # ≈4.02

KIWI_SLUGS = {
    "KGS":"kos-greece","RHO":"rhodes-greece","CFU":"corfu-greece",
    "ATH":"athens-greece","SKG":"thessaloniki-greece","HER":"heraklion-crete-greece",
    "CHQ":"chania-crete-greece","JTR":"santorini-greece","JMK":"mykonos-greece",
    "ZTH":"zakynthos-greece","EFL":"kefalonia-greece","PVK":"preveza-greece",
    "JSI":"skiathos-greece","SMI":"samos-greece","PRG":"prague-czechia",
    "BUD":"budapest-hungary","VIE":"vienna-austria","BCN":"barcelona-spain",
    "CDG":"paris-france","LHR":"london-united-kingdom","FCO":"rome-italy",
    "AMS":"amsterdam-netherlands","DXB":"dubai-united-arab-emirates",
    "BKK":"bangkok-thailand","JFK":"new-york-united-states","BER":"berlin-germany",
}


def get_search_windows():
    now = datetime.utcnow()
    out = []
    next_friday = now + timedelta(days=(4 - now.weekday()) % 7 + 7)
    out.append({"label":"סוף שבוע הקרוב","dep":next_friday.strftime("%Y-%m-%d"),
                "ret":(next_friday+timedelta(days=3)).strftime("%Y-%m-%d"),"icon":"🚀"})
    in_2w = now + timedelta(days=14)
    out.append({"label":"בעוד שבועיים","dep":in_2w.strftime("%Y-%m-%d"),
                "ret":(in_2w+timedelta(days=5)).strftime("%Y-%m-%d"),"icon":"📅"})
    jul_15 = datetime(2026,7,15)
    if jul_15 < now: jul_15 = datetime(2027,7,15)
    out.append({"label":"אמצע יולי","dep":jul_15.strftime("%Y-%m-%d"),
                "ret":(jul_15+timedelta(days=7)).strftime("%Y-%m-%d"),"icon":"☀️"})
    aug_15 = datetime(2026,8,15)
    if aug_15 < now: aug_15 = datetime(2027,8,15)
    out.append({"label":"אמצע אוגוסט","dep":aug_15.strftime("%Y-%m-%d"),
                "ret":(aug_15+timedelta(days=7)).strftime("%Y-%m-%d"),"icon":"🏖️"})
    return out


def build_search_links(origin, dest, dep_date, ret_date):
    dt_dep = datetime.strptime(dep_date, "%Y-%m-%d")
    dt_ret = datetime.strptime(ret_date, "%Y-%m-%d")
    d8d    = dt_dep.strftime("%Y%m%d")
    d8r    = dt_ret.strftime("%Y%m%d")
    slug   = KIWI_SLUGS.get(dest, dest.lower())
    return {
        "Skyscanner":     f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{d8d}/{d8r}/?adults=1&cabinclass=economy&stops=!twoPlusStops",
        "Google Flights": f"https://www.google.com/travel/flights/search?q=flights+from+{origin}+to+{dest}+on+{dep_date}+returning+{ret_date}",
        "Kiwi.com":       f"https://www.kiwi.com/en/search/results/tel-aviv-israel/{slug}/{dep_date}/{ret_date}?stops=0&adults=1",
        "Wizz Air":       f"https://wizzair.com/#/booking/select-flight/{origin}/{dest}/{dep_date}/{ret_date}/1/0/0/null",
        "Kayak":          f"https://www.kayak.com/flights/{origin}-{dest}/{dep_date}/{ret_date}?sort=price_a&fs=stops=0",
        "Aviasales":      f"https://www.aviasales.com/search/{origin}{d8d[4:]}{dest}{d8r[4:]}1",
    }


# ─── Direct airline APIs ─────────────────────────────────────────────────────

class WizzAirDirect:
    """
    Wizz Air's own public farechart API. No auth needed.
    Returns prices for a 3-day window around the target date.
    """
    URL = "https://be.wizzair.com/27.5.0/Api/asset/farechart"
    HEADERS = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://wizzair.com",
        "Referer": "https://wizzair.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    # Wizz only flies these routes from TLV
    TLV_ROUTES = {"ATH","SKG","BUD","VIE","WAW","PRG","FCO","NAP","CTA","CAG",
                  "KTW","KRK","GDN","WRO","DBV","SPU","BJV","TIA","ABZ",
                  "LCJ","SOF","OTP","CLJ","TGM","IAS","KIV","TBS","EVN","KGS"}

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_price(self, origin, dest, target_date):
        if dest not in self.TLV_ROUTES:
            return None
        try:
            r = self.session.post(self.URL, json={
                "isRescueFare": False,
                "isFlightChange": False,
                "adultCount": 1,
                "childCount": 0,
                "dayInterval": 3,
                "wdc": True,
                "flightList": [{
                    "departureStation": origin,
                    "arrivalStation":   dest,
                    "date":             target_date,
                }],
            }, timeout=12)
            if r.status_code != 200:
                return None
            data = r.json()
            flights = data.get("outboundFlights", [])
            if not flights:
                return None
            # Pick cheapest within ±3 days
            target = datetime.strptime(target_date, "%Y-%m-%d")
            best = None
            for f in flights:
                price_obj = f.get("price", {})
                amount = price_obj.get("amount", 0)
                if not amount: continue
                currency = price_obj.get("currencyCode", "EUR")
                if currency == "EUR":
                    price_ils = round(float(amount) * ILS_PER_EUR)
                elif currency == "ILS":
                    price_ils = int(amount)
                elif currency == "USD":
                    price_ils = round(float(amount) * ILS_PER_USD)
                else:
                    continue
                if price_ils <= 0: continue
                dep_at = f.get("departureDate", target_date)
                try:
                    d = datetime.strptime(dep_at[:10], "%Y-%m-%d")
                    if abs((d-target).days) > 3: continue
                except: pass
                if best is None or price_ils < best["price_ils"]:
                    best = {
                        "price_ils": price_ils,
                        "transfers": 0,
                        "airline":   "Wizz Air",
                        "departure_at": dep_at,
                        "match_date": dep_at[:10],
                        "source":    "Wizz Air",
                    }
            time.sleep(0.5)
            return best
        except Exception as e:
            logger.warning(f"[WizzAir] {origin}→{dest}: {e}")
            return None


class RyanairDirect:
    """
    Ryanair's public farfnd API. No auth.
    Useful for: BKK is not covered, but many EU routes.
    """
    URL = "https://services-api.ryanair.com/farfnd/v4/oneWayFares"
    HEADERS = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    }

    # Ryanair doesn't fly from TLV directly to many places but operates some routes
    TLV_ROUTES = {"BUD","KRK","WRO","KTW","PSA","BLQ","TSR","CTA","RHO",
                  "KGS","TLV-ATH-route","CFU","JMK","JTR","HER"}

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(self.HEADERS)

    def get_price(self, origin, dest, target_date):
        if dest not in self.TLV_ROUTES:
            return None
        try:
            # Look ±3 days
            target = datetime.strptime(target_date, "%Y-%m-%d")
            date_from = (target - timedelta(days=3)).strftime("%Y-%m-%d")
            date_to   = (target + timedelta(days=3)).strftime("%Y-%m-%d")
            r = self.s.get(self.URL, params={
                "departureAirportIataCode": origin,
                "arrivalAirportIataCode":   dest,
                "outboundDepartureDateFrom": date_from,
                "outboundDepartureDateTo":   date_to,
                "adultCount": 1,
                "currency":   "ILS",
                "market":     "en-il",
            }, timeout=12)
            if r.status_code != 200:
                return None
            fares = r.json().get("fares", [])
            best = None
            for f in fares:
                outb = f.get("outbound", {})
                price = outb.get("price", {}).get("value", 0)
                if not price or price <= 0:
                    continue
                price_ils = int(price)
                if best is None or price_ils < best["price_ils"]:
                    best = {
                        "price_ils":    price_ils,
                        "transfers":    0,
                        "airline":      "Ryanair",
                        "departure_at": outb.get("departureDate", target_date),
                        "match_date":   outb.get("departureDate", target_date)[:10],
                        "source":       "Ryanair",
                    }
            time.sleep(0.5)
            return best
        except Exception as e:
            logger.warning(f"[Ryanair] {origin}→{dest}: {e}")
            return None


class AviasalesPriceFinder:
    """
    Travelpayouts Data API (Aviasales cache).
    With token: full coverage. Without: very limited.
    Sign up: https://www.travelpayouts.com — instant, free.
    Token: https://www.travelpayouts.com/programs/100/tools/api
    """
    URL_CAL = "https://api.travelpayouts.com/v1/prices/calendar"
    URL_MAT = "https://api.travelpayouts.com/v2/prices/month-matrix"
    URL_LAT = "https://api.travelpayouts.com/v2/prices/latest"
    URL_DATES = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    def __init__(self):
        self.token = os.environ.get("AVIASALES_TOKEN", "")
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 FlightScanner"
        if self.token:
            self.s.headers["X-Access-Token"] = self.token
            logger.info(f"[Travelpayouts] ✅ token set ({len(self.token)} chars)")
        else:
            logger.warning("[Travelpayouts] ⚠️ no AVIASALES_TOKEN — limited data")
        self._cache = {}

    def get(self, origin, dest, target_date):
        month = target_date[:7]
        key = (origin, dest, month)
        if key not in self._cache:
            self._cache[key] = self._fetch_month(origin, dest, month)

        prices = self._cache[key]
        if not prices: return None

        target = datetime.strptime(target_date, "%Y-%m-%d")
        best = None
        for date_str, info in prices.items():
            try:
                d = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except: continue
            if abs((d - target).days) > 3: continue
            if best is None or info["price_ils"] < best["price_ils"]:
                best = {**info, "match_date": date_str, "source": "Aviasales"}
        return best

    def _fetch_month(self, origin, dest, month):
        # v3 prices_for_dates returns DETAILED list with airline, transfers, dates
        # This is the most powerful endpoint when token is set
        endpoints = [
            ("v3_dates", self.URL_DATES, {
                "origin": origin, "destination": dest,
                "departure_at": month,
                "currency": "usd", "limit": 30,
                "sorting": "price", "direct": "false",
            }),
            ("matrix",   self.URL_MAT, {
                "origin": origin, "destination": dest,
                "currency": "usd", "show_to_affiliates": "false",
            }),
            ("calendar", self.URL_CAL, {
                "origin": origin, "destination": dest,
                "depart_date": month, "calendar_type": "departure_date",
                "currency": "USD",
            }),
        ]
        for src, url, params in endpoints:
            try:
                r = self.s.get(url, params=params, timeout=10)
                if r.status_code != 200:
                    logger.info(f"[TP-{src}] {origin}→{dest} HTTP {r.status_code}")
                    continue
                payload = r.json()
                data = payload.get("data", {})
                if not data:
                    continue

                result = {}
                # v3 returns list of objects, matrix returns list, calendar returns dict
                items = []
                if isinstance(data, list):
                    for f in data:
                        d = f.get("departure_at", f.get("depart_date", ""))
                        if d: items.append((d[:10], f))
                elif isinstance(data, dict):
                    for k, v in data.items():
                        items.append((k, v))

                for date_str, info in items:
                    if not date_str or not date_str.startswith(month):
                        continue
                    price = float(info.get("price", info.get("value", 0)))
                    if price <= 0: continue
                    transfers = int(info.get("transfers", info.get("number_of_changes", 0)))
                    if transfers > 1: continue
                    result[date_str] = {
                        "price_ils":    round(price * ILS_PER_USD),
                        "transfers":    transfers,
                        "airline":      info.get("airline", info.get("gate", "?")),
                        "departure_at": info.get("departure_at", date_str),
                    }
                if result:
                    logger.info(f"[TP-{src}] {origin}→{dest} {month}: {len(result)} prices ✅")
                    time.sleep(0.3)
                    return result
                else:
                    logger.info(f"[TP-{src}] {origin}→{dest} {month}: empty")
            except Exception as e:
                logger.warning(f"[TP-{src}] {origin}→{dest} {month}: {e}")
        return {}




class AmadeusClient:
    """
    Amadeus Self-Service API.
    Free tier: 2000 requests/month, REAL GDS prices.
    Sign up: https://developers.amadeus.com/register
    """
    AUTH_URL   = "https://test.api.amadeus.com/v1/security/oauth2/token"
    SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    def __init__(self):
        self.client_id     = os.environ.get("AMADEUS_CLIENT_ID", "")
        self.client_secret = os.environ.get("AMADEUS_CLIENT_SECRET", "")
        self.token         = ""
        self.session       = requests.Session()
        if self.client_id and self.client_secret:
            self._authenticate()

    def _authenticate(self):
        try:
            r = self.session.post(self.AUTH_URL, data={
                "grant_type":    "client_credentials",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            }, timeout=12)
            r.raise_for_status()
            self.token = r.json().get("access_token", "")
            if self.token:
                logger.info("[Amadeus] ✅ authenticated")
        except Exception as e:
            logger.warning(f"[Amadeus] auth failed: {e}")
            self.token = ""

    def get_price(self, origin, dest, target_date):
        if not self.token:
            return None
        try:
            r = self.session.get(self.SEARCH_URL, headers={
                "Authorization": f"Bearer {self.token}",
            }, params={
                "originLocationCode":      origin,
                "destinationLocationCode": dest,
                "departureDate":           target_date,
                "adults":                  1,
                "nonStop":                 "false",
                "currencyCode":            "ILS",
                "max":                     5,
            }, timeout=20)
            if r.status_code == 401:
                logger.warning("[Amadeus] token expired, re-auth")
                self._authenticate()
                return None
            if r.status_code != 200:
                return None
            offers = r.json().get("data", [])
            best = None
            for offer in offers:
                price = float(offer.get("price", {}).get("grandTotal", 0))
                if price <= 0: continue
                itineraries = offer.get("itineraries", [])
                if not itineraries: continue
                segments = itineraries[0].get("segments", [])
                stops    = len(segments) - 1
                if stops > 1: continue
                first_seg = segments[0] if segments else {}
                airline   = first_seg.get("carrierCode", "?")
                dep_at    = first_seg.get("departure", {}).get("at", target_date)
                if best is None or price < best["price_ils"]:
                    best = {
                        "price_ils":    int(price),
                        "transfers":    stops,
                        "airline":      airline,
                        "departure_at": dep_at,
                        "match_date":   dep_at[:10],
                        "source":       "Amadeus",
                    }
            time.sleep(0.3)
            return best
        except Exception as e:
            logger.warning(f"[Amadeus] {origin}→{dest}: {e}")
            return None


def find_price(origin, dest, target_date, wizz, ryanair, aviasales, amadeus):
    """Try all sources, return cheapest verified price."""
    candidates = []
    p0 = amadeus.get_price(origin, dest, target_date)
    if p0: candidates.append(p0)
    p1 = wizz.get_price(origin, dest, target_date)
    if p1: candidates.append(p1)
    p2 = ryanair.get_price(origin, dest, target_date)
    if p2: candidates.append(p2)
    p3 = aviasales.get(origin, dest, target_date)
    if p3: candidates.append(p3)

    if not candidates: return None
    return min(candidates, key=lambda x: x["price_ils"])


def build_search_hub(focus_query=""):
    windows  = get_search_windows()
    amadeus  = AmadeusClient()
    wizz     = WizzAirDirect()
    ryanair  = RyanairDirect()
    av       = AviasalesPriceFinder()
    targets  = DESTINATIONS

    if focus_query:
        q = focus_query.strip().upper()
        targets = [d for d in DESTINATIONS if q in d["code"] or q in d["name"].upper()]
        if not targets:
            words = focus_query.lower().split()
            targets = [d for d in DESTINATIONS if any(w in d["name"] for w in words)]
        if not targets:
            targets = DESTINATIONS

    results = []
    for d in targets:
        code        = d["code"]
        rules       = DEST_RULES.get(code, {})
        months_only = rules.get("months_only", [])

        dest_windows = []
        for w in windows:
            if months_only and int(w["dep"][5:7]) not in months_only:
                continue
            price_info = find_price("TLV", code, w["dep"], wizz, ryanair, av, amadeus)
            dest_windows.append({
                **w,
                "links": build_search_links("TLV", code, w["dep"], w["ret"]),
                "price": price_info,
            })

        if not dest_windows: continue

        priced = [w for w in dest_windows if w.get("price")]
        cheapest = min(priced, key=lambda x: x["price"]["price_ils"]) if priced else None

        results.append({
            **d,
            "windows": dest_windows,
            "best_price":         cheapest["price"] if cheapest else None,
            "best_window_label":  cheapest["label"] if cheapest else None,
        })

    priced     = [r for r in results if r.get("best_price")]
    unpriced   = [r for r in results if not r.get("best_price")]
    priced.sort(key=lambda x: x["best_price"]["price_ils"])
    final = priced + unpriced

    logger.info(f"Hub: {len(final)} destinations | priced: {len(priced)}")
    return {"destinations": final, "n_priced": len(priced), "n_total": len(final)}
