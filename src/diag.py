import requests, os, json, sys

key = os.environ.get("SERPAPI_KEY","")
print(f"SERPAPI_KEY: {len(key)} chars")

# Check account quota
try:
    r = requests.get("https://serpapi.com/account",
        params={"api_key": key}, timeout=10)
    d = r.json()
    print(f"Account HTTP: {r.status_code}")
    print(f"Plan: {d.get('plan_name')}")
    print(f"Searches this month: {d.get('this_month_usage')}")
    print(f"Searches left: {d.get('searches_left')}")
    if "error" in d:
        print(f"ERROR: {d['error']}")
        sys.exit(1)
except Exception as e:
    print(f"Account check error: {e}")

# Test one real search
try:
    r2 = requests.get("https://serpapi.com/search", params={
        "engine": "google_flights",
        "departure_id": "TLV", "arrival_id": "ATH",
        "outbound_date": "2026-07-10",
        "travel_class": 1, "stops": 2,
        "currency": "ILS", "hl": "iw",
        "api_key": key,
    }, timeout=20)
    d2 = r2.json()
    print(f"Search HTTP: {r2.status_code}")
    if "error" in d2:
        print(f"Search ERROR: {d2['error']}")
    else:
        flights = d2.get("best_flights",[]) + d2.get("other_flights",[])
        print(f"Flights returned: {len(flights)}")
        for f in flights[:5]:
            legs   = f.get("flights",[])
            price  = f.get("price",0)
            stops  = len(legs)-1
            dep    = legs[0].get("departure_airport",{}).get("time","?") if legs else "?"
            airline= legs[0].get("airline","?") if legs else "?"
            print(f"  ILS{price} | stops={stops} | {dep} | {airline}")
except Exception as e:
    print(f"Search error: {e}")
