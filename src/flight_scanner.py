"""
Flight Scanner v6 — Focused SerpAPI strategy.
- 5 priority destinations only (Greek islands + Prague Jul-Aug)
- 2 date windows per destination
- Once-daily run = ~10 SerpAPI calls/day = ~300/month (close to 250 free)
- Quota check before scanning
- No email if no prices found
"""
import os, logging, requests, time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Priority destinations only
DESTINATIONS = [
    {"code": "EFL", "name": "קפלוניה",           "flag": "🇬🇷", "category": "greek"},
    {"code": "CFU", "name": "קורפו",             "flag": "🇬🇷", "category": "greek"},
    {"code": "PVK", "name": "לפקדה / פרבזה",      "flag": "🇬🇷", "category": "greek"},
    {"code": "SKG", "name": "סלוניקי / חלקידיקי", "flag": "🇬🇷", "category": "greek"},
    {"code": "PRG", "name": "פראג",              "flag": "🇨🇿", "category": "europe",
     "months_only": [7, 8]},
]

ILS_PER_USD   = 3.7
MAX_PRICE_ILS = 3500

KIWI_SLUGS = {
    "EFL":"kefalonia-greece","CFU":"corfu-greece","PVK":"preveza-greece",
    "SKG":"thessaloniki-greece","PRG":"prague-czechia",
}


def get_search_windows():
    """2 strategic date windows — focused around peak summer season."""
    now = datetime.utcnow()
    windows = []

    # Window 1: 3 weeks ahead, 5-day trip
    d1 = now + timedelta(days=21)
    windows.append({
        "label": "בעוד 3 שבועות",
        "dep":   d1.strftime("%Y-%m-%d"),
        "ret":   (d1 + timedelta(days=5)).strftime("%Y-%m-%d"),
        "icon":  "📅",
    })

    # Window 2: 6 weeks ahead, 7-day trip
    d2 = now + timedelta(days=42)
    windows.append({
        "label": "בעוד 6 שבועות",
        "dep":   d2.strftime("%Y-%m-%d"),
        "ret":   (d2 + timedelta(days=7)).strftime("%Y-%m-%d"),
        "icon":  "☀️",
    })

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


class SerpAPIClient:
    """Google Flights via SerpAPI. 250 free/month."""
    BASE = "https://serpapi.com"

    def __init__(self):
        self.key = os.environ.get("SERPAPI_KEY", "")
        self.session = requests.Session()
        self.searches_left = None

    def check_quota(self):
        if not self.key:
            return 0
        try:
            r = self.session.get(f"{self.BASE}/account",
                params={"api_key": self.key}, timeout=10)
            d = r.json()
            self.searches_left = d.get("searches_left", 0)
            logger.info(f"[SerpAPI] Plan: {d.get('plan_name')} | "
                        f"Used this month: {d.get('this_month_usage')} | "
                        f"Left: {self.searches_left}")
            return self.searches_left
        except Exception as e:
            logger.warning(f"[SerpAPI] quota check failed: {e}")
            return 0

    def search_one_way(self, origin, dest, dep_date):
        """Return cheapest verified price for this route+date."""
        if not self.key:
            return None
        try:
            r = self.session.get(f"{self.BASE}/search", params={
                "engine":       "google_flights",
                "departure_id": origin,
                "arrival_id":   dest,
                "outbound_date": dep_date,
                "travel_class": 1,
                "stops":        2,
                "currency":     "ILS",
                "hl":           "iw",
                "type":         2,    # 2 = one-way
                "api_key":      self.key,
            }, timeout=25)

            if r.status_code == 429:
                logger.error("[SerpAPI] QUOTA EXCEEDED")
                return None

            data = r.json()
            if "error" in data:
                logger.warning(f"[SerpAPI] {origin}→{dest} {dep_date}: {data['error']}")
                return None

            flights = data.get("best_flights", []) + data.get("other_flights", [])
            if not flights:
                logger.info(f"[SerpAPI] {origin}→{dest} {dep_date}: 0 flights")
                return None

            best = None
            for f in flights:
                price = f.get("price", 0)
                if not price or price <= 0:
                    continue
                legs = f.get("flights", [])
                stops = len(legs) - 1
                if stops > 1:
                    continue
                dep = legs[0].get("departure_airport", {}).get("time", dep_date) if legs else dep_date
                arr = legs[-1].get("arrival_airport", {}).get("time", "") if legs else ""
                airline = legs[0].get("airline", "?") if legs else "?"
                if best is None or price < best["price_ils"]:
                    best = {
                        "price_ils":    int(price),
                        "transfers":    stops,
                        "airline":      airline,
                        "departure_at": dep,
                        "arrival_at":   arr,
                        "match_date":   dep[:10],
                        "duration":     f.get("total_duration", 0),
                        "source":       "Google Flights",
                    }

            if best:
                logger.info(f"[SerpAPI] {origin}→{dest} {dep_date}: "
                            f"₪{best['price_ils']:,} {best['airline']} stops={best['transfers']}")
            time.sleep(1.2)
            return best
        except Exception as e:
            logger.warning(f"[SerpAPI] {origin}→{dest}: {e}")
            return None


def build_search_hub(focus_query=""):
    """Main entry: scan priority destinations and return structured hub."""
    serp = SerpAPIClient()
    windows = get_search_windows()

    quota = serp.check_quota()
    needed = len(DESTINATIONS) * len(windows)   # max calls this run
    logger.info(f"Need up to {needed} SerpAPI calls | Have {quota} left")
    if quota < needed:
        logger.warning(f"⚠️ Quota low ({quota}) — may not complete all destinations")

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
            price_info = serp.search_one_way("TLV", code, w["dep"])
            dest_windows.append({
                **w,
                "links": build_search_links("TLV", code, w["dep"], w["ret"]),
                "price": price_info if price_info and price_info["price_ils"] <= MAX_PRICE_ILS else None,
            })

        if not dest_windows:
            continue

        priced = [w for w in dest_windows if w.get("price")]
        cheapest = min(priced, key=lambda x: x["price"]["price_ils"]) if priced else None

        results.append({
            **d,
            "windows": dest_windows,
            "best_price":        cheapest["price"] if cheapest else None,
            "best_window_label": cheapest["label"] if cheapest else None,
        })

    # Sort: priced (low→high) first, then unpriced
    priced     = [r for r in results if r.get("best_price")]
    unpriced   = [r for r in results if not r.get("best_price")]
    priced.sort(key=lambda x: x["best_price"]["price_ils"])
    final = priced + unpriced

    logger.info(f"=== {len(priced)}/{len(final)} destinations with verified prices ===")
    return {
        "destinations": final,
        "n_priced":     len(priced),
        "n_total":      len(final),
        "quota_left":   serp.searches_left or 0,
    }
