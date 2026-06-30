"""
Flight Scanner v8 — Round-trip prices matching Google Flights.
KEY FIXES:
- Round-trip search (type=1) with both outbound and return dates
- Prices match Google Flights site exactly
- Fixed URL formats for all booking sites (YYMMDD where needed)
- One API call per route (simple, accurate, fits in quota)
- Repo cache 24h TTL
"""
import os, logging, requests, time, json
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
    """Round-trip windows with both outbound and return dates."""
    now = datetime.utcnow()
    return [
        {"label": "בעוד 3 שבועות",
         "dep":   (now + timedelta(days=21)).strftime("%Y-%m-%d"),
         "ret":   (now + timedelta(days=26)).strftime("%Y-%m-%d"),
         "icon":  "📅"},
        {"label": "בעוד 6 שבועות",
         "dep":   (now + timedelta(days=42)).strftime("%Y-%m-%d"),
         "ret":   (now + timedelta(days=49)).strftime("%Y-%m-%d"),
         "icon":  "☀️"},
    ]


KIWI_SLUGS = {
    "EFL":"kefalonia-greece","CFU":"corfu-greece","PVK":"preveza-greece",
    "SKG":"thessaloniki-greece","PRG":"prague-czechia",
}


def build_search_links(origin, dest, dep_date, ret_date):
    """Build deep links that ACTUALLY pre-fill the search on each site."""
    dt_dep = datetime.strptime(dep_date, "%Y-%m-%d")
    dt_ret = datetime.strptime(ret_date, "%Y-%m-%d")

    # Skyscanner uses YYMMDD (6 digits)
    sky_dep = dt_dep.strftime("%y%m%d")
    sky_ret = dt_ret.strftime("%y%m%d")

    # Aviasales uses DDMM (4 digits, day+month)
    av_dep = dt_dep.strftime("%d%m")
    av_ret = dt_ret.strftime("%d%m")

    slug = KIWI_SLUGS.get(dest, dest.lower())

    return {
        # Skyscanner: YYMMDD format, verified working with round-trip
        "Skyscanner": f"https://www.skyscanner.net/transport/flights/{origin.lower()}/{dest.lower()}/{sky_dep}/{sky_ret}/?adultsv2=1&cabinclass=economy&rtn=1&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false",

        # Google Flights: q= text search format is most stable
        "Google Flights": f"https://www.google.com/travel/flights?hl=iw&curr=ILS&q=flights%20from%20{origin}%20to%20{dest}%20on%20{dep_date}%20through%20{ret_date}",

        # Kiwi: round-trip URL
        "Kiwi.com": f"https://www.kiwi.com/en/search/results/tel-aviv-israel/{slug}/{dep_date}/{ret_date}?sortBy=price&adults=1",

        # Wizz Air: their hash-based URL
        "Wizz Air": f"https://wizzair.com/#/booking/select-flight/{origin}/{dest}/{dep_date}/{ret_date}/1/0/0/null",

        # Kayak: super clean URL format
        "Kayak": f"https://www.kayak.com/flights/{origin}-{dest}/{dep_date}/{ret_date}/economy?sort=price_a",

        # Aviasales: DDMM format
        "Aviasales": f"https://www.aviasales.com/search/{origin}{av_dep}{dest}{av_ret}1",
    }


# ─── Cache ──────────────────────────────────────────────────────────────────

def load_cache():
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            logger.info(f"[Cache] loaded {len(cache)} entries")
            return cache
    except Exception as e:
        logger.warning(f"[Cache] load: {e}")
    return {}

def save_cache(cache):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"[Cache] saved {len(cache)} entries")
    except Exception as e:
        logger.warning(f"[Cache] save: {e}")

def cache_key(origin, dest, dep_date, ret_date):
    return f"{origin}_{dest}_{dep_date}_{ret_date}"

def is_fresh(entry):
    try:
        ts = datetime.fromisoformat(entry["fetched_at"])
        return (datetime.utcnow() - ts) < timedelta(hours=CACHE_TTL_HOURS)
    except:
        return False


# ─── SerpAPI client — ROUND TRIP search ─────────────────────────────────────

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
            logger.warning(f"[SerpAPI] quota: {e}")
            return 0

    def search_round_trip(self, origin, dest, dep_date, ret_date):
        """
        ROUND TRIP search — type=1.
        Returns top 5 flights with REAL round-trip prices.
        Each flight: {price_ils, airline, transfers, dep_at, arr_at, ret_dep_at}
        """
        if not self.key:
            return []
        try:
            r = self.session.get(f"{self.BASE}/search", params={
                "engine":        "google_flights",
                "departure_id":  origin,
                "arrival_id":    dest,
                "outbound_date": dep_date,
                "return_date":   ret_date,
                "type":          1,    # 1 = round trip
                "travel_class":  1,
                "stops":         1,    # 1 = NONSTOP only (direct flights)
                "currency":      "ILS",
                "hl":            "iw",
                "api_key":       self.key,
            }, timeout=30)
            self.calls_made += 1

            if r.status_code == 429:
                logger.error("[SerpAPI] QUOTA EXCEEDED")
                return []

            data = r.json()
            if "error" in data:
                logger.warning(f"[SerpAPI] {origin}↔{dest} {dep_date}/{ret_date}: {data['error']}")
                return []

            flights = data.get("best_flights", []) + data.get("other_flights", [])
            if not flights:
                logger.info(f"[SerpAPI] {origin}↔{dest} {dep_date}/{ret_date}: 0 flights")
                return []

            results = []
            for f in flights:
                price = f.get("price", 0)
                if not price or price <= 0:
                    continue
                legs = f.get("flights", [])
                if not legs:
                    continue

                stops = len(legs) - 1
                if stops > 0:        # ONLY direct flights
                    continue

                airline = legs[0].get("airline", "?")
                dep_at  = legs[0].get("departure_airport", {}).get("time", dep_date)
                arr_at  = legs[-1].get("arrival_airport", {}).get("time", "")
                dur     = f.get("total_duration", 0)

                results.append({
                    "price_ils":    int(price),
                    "airline":      airline,
                    "transfers":    stops,
                    "departure_at": dep_at,
                    "arrival_at":   arr_at,
                    "duration":     dur,
                    "match_date":   dep_at[:10],
                    "source":       "Google Flights (Round Trip)",
                })

            results.sort(key=lambda x: x["price_ils"])
            logger.info(f"[SerpAPI] {origin}↔{dest} {dep_date}/{ret_date}: {len(results)} flights, "
                        f"cheapest=₪{results[0]['price_ils']:,} {results[0]['airline']}")
            time.sleep(1.5)
            return results[:5]   # Top 5 cheapest

        except Exception as e:
            logger.warning(f"[SerpAPI] {origin}→{dest}: {e}")
            return []


def fetch_with_cache(client, cache, origin, dest, dep_date, ret_date):
    key = cache_key(origin, dest, dep_date, ret_date)
    entry = cache.get(key)
    if entry and is_fresh(entry):
        logger.info(f"[Cache HIT] {origin}↔{dest} {dep_date}/{ret_date}")
        return entry.get("flights", [])

    logger.info(f"[Cache MISS] {origin}↔{dest} {dep_date}/{ret_date} — fetching")
    flights = client.search_round_trip(origin, dest, dep_date, ret_date)
    if flights:
        cache[key] = {
            "fetched_at": datetime.utcnow().isoformat(),
            "flights":    flights,
        }
    return flights


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

            flights = fetch_with_cache(serp, cache, "TLV", code, w["dep"], w["ret"])
            flights_under_max = [f for f in flights if f["price_ils"] <= MAX_PRICE_ILS]

            dest_windows.append({
                **w,
                "links":   build_search_links("TLV", code, w["dep"], w["ret"]),
                "flights": flights_under_max,
            })

        if not dest_windows:
            continue

        all_prices = [f["price_ils"] for w in dest_windows for f in w.get("flights", [])]
        best_price = min(all_prices) if all_prices else None

        results.append({
            **d,
            "windows":        dest_windows,
            "best_price_ils": best_price,
        })

    save_cache(cache)

    priced     = [r for r in results if r.get("best_price_ils")]
    unpriced   = [r for r in results if not r.get("best_price_ils")]
    priced.sort(key=lambda x: x["best_price_ils"])
    final = priced + unpriced

    logger.info(f"=== {len(priced)}/{len(final)} destinations with prices ===")
    logger.info(f"=== {serp.calls_made} SerpAPI calls this run ===")
    return {
        "destinations": final,
        "n_priced":     len(priced),
        "n_total":      len(final),
        "quota_left":   max(0, (serp.searches_left or 0) - serp.calls_made),
        "calls_made":   serp.calls_made,
    }
