"""
Flight Scanner v7 — Per-OTA verified prices via SerpAPI booking_options.
- Step 1: Google Flights search → get flight options with departure_token
- Step 2: Use departure_token to fetch booking_options → get exact price per OTA
- Each price labeled with the actual OTA (Skyscanner, Kiwi, Gotogate, EL AL, etc.)
- 24h cache in repo (cache/prices.json) to avoid burning quota
- Strict: no prices = no email
"""

import os, logging, requests, time, json, hashlib
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DESTINATIONS = [
    {"code": "EFL", "name": "קפלוניה",           "flag": "🇬🇷", "category": "greek"},
    {"code": "CFU", "name": "קורפו",             "flag": "🇬🇷", "category": "greek"},
    {"code": "PVK", "name": "לפקדה / פרבזה",      "flag": "🇬🇷", "category": "greek"},
    {"code": "SKG", "name": "סלוניקי / חלקידיקי", "flag": "🇬🇷", "category": "greek"},
    {"code": "PRG", "name": "פראג",              "flag": "🇨🇿", "category": "europe",
     "months_only": [7, 8]},
]

MAX_PRICE_ILS = 3500
CACHE_FILE    = Path(__file__).parent.parent / "cache" / "prices.json"
CACHE_TTL_HOURS = 24


def get_search_windows():
    now = datetime.utcnow()
    return [
        {"label": "בעוד 3 שבועות",
         "dep": (now + timedelta(days=21)).strftime("%Y-%m-%d"),
         "ret": (now + timedelta(days=26)).strftime("%Y-%m-%d"),
         "icon": "📅"},
        {"label": "בעוד 6 שבועות",
         "dep": (now + timedelta(days=42)).strftime("%Y-%m-%d"),
         "ret": (now + timedelta(days=49)).strftime("%Y-%m-%d"),
         "icon": "☀️"},
    ]


KIWI_SLUGS = {
    "EFL":"kefalonia-greece","CFU":"corfu-greece","PVK":"preveza-greece",
    "SKG":"thessaloniki-greece","PRG":"prague-czechia",
}


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


# ─── Cache (repo-committed) ─────────────────────────────────────────────────

def load_cache():
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            logger.info(f"[Cache] loaded {len(cache)} entries from {CACHE_FILE.name}")
            return cache
    except Exception as e:
        logger.warning(f"[Cache] load failed: {e}")
    return {}


def save_cache(cache):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"[Cache] saved {len(cache)} entries")
    except Exception as e:
        logger.warning(f"[Cache] save failed: {e}")


def cache_key(origin, dest, dep_date):
    return f"{origin}_{dest}_{dep_date}"


def is_fresh(entry):
    try:
        ts = datetime.fromisoformat(entry["fetched_at"])
        return (datetime.utcnow() - ts) < timedelta(hours=CACHE_TTL_HOURS)
    except:
        return False


# ─── SerpAPI client with two-step OTA price fetching ───────────────────────

class SerpAPIClient:
    BASE = "https://serpapi.com"

    def __init__(self):
        self.key = os.environ.get("SERPAPI_KEY", "")
        self.session = requests.Session()
        self.calls_made = 0
        self.searches_left = None

    def check_quota(self):
        if not self.key:
            return 0
        try:
            r = self.session.get(f"{self.BASE}/account",
                params={"api_key": self.key}, timeout=10)
            d = r.json()
            self.searches_left = d.get("searches_left", 0)
            logger.info(f"[SerpAPI] Plan={d.get('plan_name')} "
                        f"Used={d.get('this_month_usage')} "
                        f"Left={self.searches_left}")
            return self.searches_left
        except Exception as e:
            logger.warning(f"[SerpAPI] quota check: {e}")
            return 0

    def fetch_flights_with_ota_prices(self, origin, dest, dep_date):
        """
        Two-step fetch:
        1. Search Google Flights → get best flight + booking_token
        2. Fetch booking_options for that flight → list of OTAs with their prices
        Returns: list of {ota_name, price_ils, airline, transfers, ...}
        """
        if not self.key:
            return None

        # Step 1: search
        try:
            r = self.session.get(f"{self.BASE}/search", params={
                "engine":        "google_flights",
                "departure_id":  origin,
                "arrival_id":    dest,
                "outbound_date": dep_date,
                "type":          2,    # one-way
                "travel_class":  1,
                "stops":         2,
                "currency":      "ILS",
                "hl":            "iw",
                "api_key":       self.key,
            }, timeout=25)
            self.calls_made += 1

            if r.status_code == 429:
                logger.error("[SerpAPI] QUOTA EXCEEDED")
                return None
            data = r.json()
            if "error" in data:
                logger.warning(f"[SerpAPI] step1 {origin}→{dest} {dep_date}: {data['error']}")
                return None

            flights = data.get("best_flights", []) + data.get("other_flights", [])
            if not flights:
                logger.info(f"[SerpAPI] {origin}→{dest} {dep_date}: 0 flights")
                return None

            # Pick the cheapest direct (or 1-stop) flight
            candidates = [f for f in flights
                          if f.get("price", 0) > 0
                          and (len(f.get("flights", [])) - 1) <= 1]
            if not candidates:
                return None
            best = min(candidates, key=lambda x: x["price"])

            legs    = best.get("flights", [])
            stops   = len(legs) - 1
            airline = legs[0].get("airline", "?") if legs else "?"
            dep_at  = legs[0].get("departure_airport", {}).get("time", dep_date) if legs else dep_date
            arr_at  = legs[-1].get("arrival_airport", {}).get("time", "") if legs else ""
            dur     = best.get("total_duration", 0)

            departure_token = best.get("departure_token")
            gf_price        = int(best["price"])
            time.sleep(1.2)

            # Step 2: get OTA booking options
            ota_prices = []
            if departure_token:
                try:
                    r2 = self.session.get(f"{self.BASE}/search", params={
                        "engine":          "google_flights",
                        "departure_id":    origin,
                        "arrival_id":      dest,
                        "outbound_date":   dep_date,
                        "type":            2,
                        "travel_class":    1,
                        "currency":        "ILS",
                        "hl":              "iw",
                        "departure_token": departure_token,
                        "api_key":         self.key,
                    }, timeout=25)
                    self.calls_made += 1

                    if r2.status_code == 200:
                        data2 = r2.json()
                        for option in data2.get("booking_options", []):
                            tg = option.get("together") or option.get("departing") or {}
                            ota_name = tg.get("book_with", "")
                            price    = tg.get("price", 0)
                            if not ota_name or not price:
                                continue
                            ota_prices.append({
                                "ota":       ota_name,
                                "price_ils": int(price),
                                "url":       tg.get("booking_request", {}).get("url", ""),
                            })
                except Exception as e:
                    logger.warning(f"[SerpAPI step2] {e}")
                time.sleep(1.2)

            # Always include Google Flights' cheapest as one row
            ota_prices.insert(0, {
                "ota":       "Google Flights (זול ביותר)",
                "price_ils": gf_price,
                "url":       "",
            })

            # Dedupe by OTA name keeping cheapest
            best_per_ota = {}
            for p in ota_prices:
                k = p["ota"].lower().strip()
                if k not in best_per_ota or p["price_ils"] < best_per_ota[k]["price_ils"]:
                    best_per_ota[k] = p
            ota_prices = sorted(best_per_ota.values(), key=lambda x: x["price_ils"])

            return {
                "flight_meta": {
                    "airline":      airline,
                    "transfers":    stops,
                    "departure_at": dep_at,
                    "arrival_at":   arr_at,
                    "duration":     dur,
                    "match_date":   dep_at[:10],
                },
                "ota_prices": ota_prices[:6],   # top 6 by price
            }

        except Exception as e:
            logger.warning(f"[SerpAPI] {origin}→{dest}: {e}")
            return None


def fetch_with_cache(client, cache, origin, dest, dep_date):
    """Return cached entry if fresh, else fetch fresh and update cache."""
    key = cache_key(origin, dest, dep_date)
    entry = cache.get(key)
    if entry and is_fresh(entry):
        logger.info(f"[Cache HIT] {origin}→{dest} {dep_date}")
        return entry.get("data")

    logger.info(f"[Cache MISS] {origin}→{dest} {dep_date} — fetching")
    data = client.fetch_flights_with_ota_prices(origin, dest, dep_date)
    if data:
        cache[key] = {
            "fetched_at": datetime.utcnow().isoformat(),
            "data":       data,
        }
    return data


def build_search_hub(focus_query=""):
    serp  = SerpAPIClient()
    cache = load_cache()
    windows = get_search_windows()

    quota = serp.check_quota()
    logger.info(f"Quota: {quota} | Cache entries: {len(cache)}")

    targets = DESTINATIONS
    if focus_query:
        q = focus_query.strip().upper()
        targets = [d for d in DESTINATIONS if q in d["code"] or q in d["name"].upper()]
        if not targets:
            targets = DESTINATIONS

    results = []
    for d in targets:
        code        = d["code"]
        months_only = d.get("months_only", [])
        dest_windows = []

        for w in windows:
            if months_only and int(w["dep"][5:7]) not in months_only:
                continue

            data = fetch_with_cache(serp, cache, "TLV", code, w["dep"])

            ota_prices = []
            flight_meta = None
            if data:
                flight_meta = data.get("flight_meta")
                ota_prices = [p for p in data.get("ota_prices", [])
                              if p["price_ils"] <= MAX_PRICE_ILS]

            dest_windows.append({
                **w,
                "links":       build_search_links("TLV", code, w["dep"], w["ret"]),
                "flight_meta": flight_meta,
                "ota_prices":  ota_prices,
            })

        if not dest_windows:
            continue

        # Best price for this destination = min across all OTA prices in all windows
        all_prices = [p["price_ils"] for w in dest_windows for p in w.get("ota_prices", [])]
        best_price_ils = min(all_prices) if all_prices else None

        results.append({
            **d,
            "windows":        dest_windows,
            "best_price_ils": best_price_ils,
        })

    save_cache(cache)

    # Sort: priced (low→high) first, unpriced last
    priced     = [r for r in results if r.get("best_price_ils")]
    unpriced   = [r for r in results if not r.get("best_price_ils")]
    priced.sort(key=lambda x: x["best_price_ils"])
    final = priced + unpriced

    logger.info(f"=== {len(priced)}/{len(final)} destinations with verified OTA prices ===")
    logger.info(f"=== SerpAPI calls this run: {serp.calls_made} ===")
    return {
        "destinations": final,
        "n_priced":     len(priced),
        "n_total":      len(final),
        "quota_left":   max(0, (serp.searches_left or 0) - serp.calls_made),
        "calls_made":   serp.calls_made,
    }
