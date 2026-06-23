"""
Flight Scanner v3 — Search Hub Strategy
No more broken APIs. Instead: builds a curated hub of search links.
For each destination + 4 date windows, generates direct search URLs to:
  - Skyscanner (real-time prices on their site)
  - Google Flights (real-time)
  - Kiwi.com
  - Wizz Air, Ryanair, Bluebird, Aegean (direct booking)
User clicks → sees real prices on the actual site. Zero fake data.
"""

import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DESTINATIONS = [
    # איי יוון — עדיפות עליונה
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
    # אירופה
    {"code": "LHR", "name": "לונדון",         "flag": "🇬🇧", "category": "europe"},
    {"code": "CDG", "name": "פריז",           "flag": "🇫🇷", "category": "europe"},
    {"code": "FCO", "name": "רומא",           "flag": "🇮🇹", "category": "europe"},
    {"code": "BCN", "name": "ברצלונה",        "flag": "🇪🇸", "category": "europe"},
    {"code": "AMS", "name": "אמסטרדם",        "flag": "🇳🇱", "category": "europe"},
    {"code": "VIE", "name": "וינה",           "flag": "🇦🇹", "category": "europe"},
    {"code": "PRG", "name": "פראג",           "flag": "🇨🇿", "category": "europe"},
    {"code": "BUD", "name": "בודפשט",         "flag": "🇭🇺", "category": "europe"},
    {"code": "BER", "name": "ברלין",          "flag": "🇩🇪", "category": "europe"},
    # מזה"ת ואסיה
    {"code": "DXB", "name": "דובאי",          "flag": "🇦🇪", "category": "asia"},
    {"code": "BKK", "name": "בנגקוק",         "flag": "🇹🇭", "category": "asia"},
    # ארה"ב
    {"code": "JFK", "name": "ניו יורק",       "flag": "🇺🇸", "category": "usa"},
]

# Prague: July-August only
DEST_RULES = {"PRG": {"months_only": [7, 8]}}

# 4 strategic date windows for each destination
def get_search_windows():
    """4 dates spread across the next 6 months."""
    now = datetime.utcnow()
    windows = []

    # Window 1: Next weekend (~5-7 days ahead)
    next_friday = now + timedelta(days=(4 - now.weekday()) % 7 + 7)
    windows.append({
        "label": "סוף שבוע הקרוב",
        "dep":   next_friday.strftime("%Y-%m-%d"),
        "ret":   (next_friday + timedelta(days=3)).strftime("%Y-%m-%d"),
        "icon":  "🚀",
    })

    # Window 2: 2 weeks ahead
    in_2w = now + timedelta(days=14)
    windows.append({
        "label": "בעוד שבועיים",
        "dep":   in_2w.strftime("%Y-%m-%d"),
        "ret":   (in_2w + timedelta(days=5)).strftime("%Y-%m-%d"),
        "icon":  "📅",
    })

    # Window 3: Mid July (peak season)
    jul_15 = datetime(2026, 7, 15)
    if jul_15 < now:
        jul_15 = datetime(2027, 7, 15)
    windows.append({
        "label": "אמצע יולי",
        "dep":   jul_15.strftime("%Y-%m-%d"),
        "ret":   (jul_15 + timedelta(days=7)).strftime("%Y-%m-%d"),
        "icon":  "☀️",
    })

    # Window 4: Mid August
    aug_15 = datetime(2026, 8, 15)
    if aug_15 < now:
        aug_15 = datetime(2027, 8, 15)
    windows.append({
        "label": "אמצע אוגוסט",
        "dep":   aug_15.strftime("%Y-%m-%d"),
        "ret":   (aug_15 + timedelta(days=7)).strftime("%Y-%m-%d"),
        "icon":  "🏖️",
    })

    return windows


# Kiwi.com city slugs
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


def build_search_links(origin, dest_code, dep_date, ret_date):
    """Build all search URLs for a destination on specific dates."""
    dt_dep = datetime.strptime(dep_date, "%Y-%m-%d")
    dt_ret = datetime.strptime(ret_date, "%Y-%m-%d")
    d8_dep = dt_dep.strftime("%Y%m%d")
    d8_ret = dt_ret.strftime("%Y%m%d")
    slug   = KIWI_SLUGS.get(dest_code, dest_code.lower())

    return {
        "Skyscanner": (
            f"https://www.skyscanner.net/transport/flights/"
            f"{origin.lower()}/{dest_code.lower()}/{d8_dep}/{d8_ret}/"
            f"?adults=1&cabinclass=economy&stops=!twoPlusStops"
        ),
        "Google Flights": (
            f"https://www.google.com/travel/flights/search"
            f"?q=flights+from+{origin}+to+{dest_code}+on+{dep_date}+returning+{ret_date}"
        ),
        "Kiwi.com": (
            f"https://www.kiwi.com/en/search/results/"
            f"tel-aviv-israel/{slug}/{dep_date}/{ret_date}"
            f"?stops=0&adults=1"
        ),
        "Wizz Air": (
            f"https://wizzair.com/#/booking/select-flight/{origin}/{dest_code}/"
            f"{dep_date}/{ret_date}/1/0/0/null"
        ),
        "Kayak": (
            f"https://www.kayak.com/flights/{origin}-{dest_code}/{dep_date}/{ret_date}"
            f"?sort=price_a&fs=stops=0"
        ),
        "Aviasales": (
            f"https://www.aviasales.com/search/{origin}{d8_dep[4:]}"
            f"{dest_code}{d8_ret[4:]}1"
        ),
    }


def build_search_hub(focus_query=""):
    """
    Returns a dict structured for the email builder:
    {
      "destinations": [
        {
          "code": "KGS",
          "name": "קוס",
          "flag": "🇬🇷",
          "category": "greek",
          "windows": [
            {"label": "...", "dep": "2026-07-04", "ret": "2026-07-07",
             "links": {"Skyscanner": "...", ...}}
          ]
        }
      ]
    }
    """
    windows  = get_search_windows()
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
        rules       = DEST_RULES.get(d["code"], {})
        months_only = rules.get("months_only", [])

        dest_windows = []
        for w in windows:
            if months_only and int(w["dep"][5:7]) not in months_only:
                continue
            dest_windows.append({
                **w,
                "links": build_search_links("TLV", d["code"], w["dep"], w["ret"]),
            })

        if dest_windows:
            results.append({
                **d,
                "windows": dest_windows,
            })

    logger.info(f"Hub built: {len(results)} destinations × {len(windows)} windows")
    return {"destinations": results}
