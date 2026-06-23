import requests, os, json, subprocess
from datetime import datetime

key = os.environ.get("SERPAPI_KEY","")
lines = [f"=== DIAG {datetime.now()} ==="]
lines.append(f"SERPAPI_KEY: {len(key)} chars")

try:
    r = requests.get("https://serpapi.com/account",
        params={"api_key": key}, timeout=10)
    d = r.json()
    lines.append(f"Account HTTP: {r.status_code}")
    lines.append(f"Plan: {d.get('plan_name')}")
    lines.append(f"Searches this month: {d.get('this_month_usage')}")
    lines.append(f"Searches left: {d.get('searches_left')}")
    if "error" in d:
        lines.append(f"ACCOUNT ERROR: {d['error']}")
except Exception as e:
    lines.append(f"Account error: {e}")

try:
    r2 = requests.get("https://serpapi.com/search", params={
        "engine": "google_flights",
        "departure_id": "TLV", "arrival_id": "ATH",
        "outbound_date": "2026-07-10",
        "travel_class": 1, "stops": 2,
        "currency": "ILS", "hl": "iw", "api_key": key,
    }, timeout=20)
    d2 = r2.json()
    lines.append(f"Search HTTP: {r2.status_code}")
    if "error" in d2:
        lines.append(f"SEARCH ERROR: {d2['error']}")
    else:
        flights = d2.get("best_flights",[]) + d2.get("other_flights",[])
        lines.append(f"Flights found: {len(flights)}")
        for f in flights[:5]:
            legs  = f.get("flights",[])
            price = f.get("price",0)
            dep   = legs[0].get("departure_airport",{}).get("time","?") if legs else "?"
            al    = legs[0].get("airline","?") if legs else "?"
            lines.append(f"  ILS{price} | stops={len(legs)-1} | {dep[:16]} | {al}")
except Exception as e:
    lines.append(f"Search error: {e}")

output = "\n".join(lines)
print(output)

# Write to diag_result.txt so it can be committed
with open("diag_result.txt","w") as f:
    f.write(output)
