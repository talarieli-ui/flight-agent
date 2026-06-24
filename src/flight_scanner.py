"""
Flight Scanner v4 — Hub + Real Prices
- Builds search hub (links to Skyscanner, Google, etc.)
- Adds REAL prices from Aviasales public cache where available
- Sorts destinations by best verified price (low→high)
- Honest: shows "no verified price" when data unavailable
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
MAX_PRICE_ILS = 3500

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
    """4 strategic date windows."""
    now = datetime.utcnow()
    windows = []

    next_friday = now + timedelta(days=(4 - now.weekday()) % 7 + 7)
    windows.append({"label":"סוף שבוע הקרוב","dep":next_friday.strftime("%Y-%m-%d"),
                    "ret":(next_friday+timedelta(days=3)).strftime("%Y-%m-%d"),"icon":"🚀"})

    in_2w = now + timedelta(days=14)
    windows.append({"label":"בעוד שבועיים","dep":in_2w.strftime("%Y-%m-%d"),
                    "ret":(in_2w+timedelta(days=5)).strftime("%Y-%m-%d"),"icon":"📅"})

    jul_15 = datetime(2026,7,15)
    if jul_15 < now: jul_15 = datetime(2027,7,15)
    windows.append({"label":"אמצע יולי","dep":jul_15.strftime("%Y-%m-%d"),
                    "ret":(jul_15+timedelta(days=7)).strftime("%Y-%m-%d"),"icon":"☀️"})

    aug_15 = datetime(2026,8,15)
    if aug_15 < now: aug_15 = datetime(2027,8,15)
    windows.append({"label":"אמצע אוגוסט","dep":aug_15.strftime("%Y-%m-%d"),
                    "ret":(aug_15+timedelta(days=7)).strftime("%Y-%m-%d"),"icon":"🏖️"})

    return windows


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


# ─────────── REAL PRICE FETCHERS ────────────────────────────────────────────

class AviasalesPriceFinder:
    """
    Free public Aviasales cache. No token needed.
    Endpoint: /v1/prices/calendar — returns price-per-day for whole month.
    """
    URL = "https://api.travelpayouts.com/v1/prices/calendar"
    URL_MATRIX = "https://api.travelpayouts.com/v2/prices/month-matrix"
    URL_LATEST = "https://api.travelpayouts.com/v2/prices/latest"

    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 FlightScanner"
        self._cache = {}   # (origin,dest,month) -> {date: price_data}

    def get_month_prices(self, origin, dest, month):
        """Returns {date_str: {price_usd, transfers, airline, departure_at}} for the month."""
        key = (origin, dest, month)
        if key in self._cache:
            return self._cache[key]

        # Try calendar endpoint first
        try:
            r = self.s.get(self.URL, params={
                "origin": origin, "destination": dest,
                "depart_date": month,
                "calendar_type": "departure_date",
                "currency": "USD",
            }, timeout=10)
            r.raise_for_status()
            data = r.json().get("data", {})
            if data:
                result = {}
                for date_str, info in data.items():
                    price = float(info.get("price", 0))
                    if price > 0:
                        result[date_str] = {
                            "price_usd":     price,
                            "price_ils":     round(price * ILS_PER_USD),
                            "transfers":     info.get("number_of_changes", info.get("transfers", 0)),
                            "airline":       info.get("gate", info.get("airline", "?")),
                            "departure_at":  info.get("departure_at", ""),
                            "return_at":     info.get("return_at", ""),
                        }
                self._cache[key] = result
                logger.info(f"[Aviasales calendar] {origin}→{dest} {month}: {len(result)} prices")
                time.sleep(0.5)
                return result
        except Exception as e:
            logger.warning(f"[Aviasales calendar] {origin}→{dest} {month}: {e}")

        # Fallback to month-matrix
        try:
            r2 = self.s.get(self.URL_MATRIX, params={
                "origin": origin, "destination": dest,
                "currency": "USD",
                "show_to_affiliates": "false",
            }, timeout=10)
            r2.raise_for_status()
            data2 = r2.json().get("data", [])
            result = {}
            for item in data2:
                dep_at = item.get("depart_date", "")
                if dep_at.startswith(month):
                    price = float(item.get("value", 0))
                    if price > 0:
                        result[dep_at] = {
                            "price_usd":    price,
                            "price_ils":    round(price * ILS_PER_USD),
                            "transfers":    item.get("number_of_changes", 0),
                            "airline":      item.get("gate", "?"),
                            "departure_at": dep_at,
                            "return_at":    item.get("return_date", ""),
                        }
            if result:
                self._cache[key] = result
                logger.info(f"[Aviasales matrix] {origin}→{dest} {month}: {len(result)} prices")
            time.sleep(0.5)
            return result
        except Exception as e:
            logger.warning(f"[Aviasales matrix] {origin}→{dest} {month}: {e}")

        self._cache[key] = {}
        return {}

    def best_for_window(self, origin, dest, dep_date, ret_date):
        """Best cached price near the given window."""
        month = dep_date[:7]
        prices = self.get_month_prices(origin, dest, month)
        if not prices:
            return None

        # Find closest date within ±3 days of target
        target = datetime.strptime(dep_date, "%Y-%m-%d")
        best = None
        for date_str, info in prices.items():
            try:
                d = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except:
                continue
            if abs((d - target).days) > 3:
                continue
            if best is None or info["price_ils"] < best["price_ils"]:
                best = {**info, "match_date": date_str}
        return best


def build_search_hub(focus_query=""):
    """Build hub + attach real prices where available."""
    windows  = get_search_windows()
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

            price_info = av.best_for_window("TLV", code, w["dep"], w["ret"])
            window = {
                **w,
                "links": build_search_links("TLV", code, w["dep"], w["ret"]),
                "price": price_info,
            }
            dest_windows.append(window)

        if not dest_windows:
            continue

        # Cheapest window for this destination
        priced = [w for w in dest_windows if w.get("price") and w["price"]["price_ils"] <= MAX_PRICE_ILS]
        cheapest = min(priced, key=lambda x: x["price"]["price_ils"]) if priced else None

        results.append({
            **d,
            "windows": dest_windows,
            "best_price": cheapest["price"] if cheapest else None,
            "best_window_label": cheapest["label"] if cheapest else None,
        })

    # Sort destinations: priced first (low→high), then unpriced
    priced     = [r for r in results if r.get("best_price")]
    unpriced   = [r for r in results if not r.get("best_price")]
    priced.sort(key=lambda x: x["best_price"]["price_ils"])

    sorted_results = priced + unpriced
    logger.info(f"Hub: {len(sorted_results)} destinations | with verified prices: {len(priced)}")
    return {"destinations": sorted_results, "n_priced": len(priced), "n_total": len(sorted_results)}
