import requests, os, base64
from datetime import datetime

KEY  = os.environ.get("RAPIDAPI_KEY","")
PAT  = os.environ.get("GH_PAT","")
REPO = "talarieli-ui/flight-agent"
GH   = {"Authorization": f"token {PAT}", "Accept": "application/vnd.github.v3+json"}
dep  = "2026-07-10"
out  = [f"DIAG {datetime.now().strftime('%H:%M')} KEY={len(KEY)}chars PAT={len(PAT)}chars"]

def test_api(label, url, host, params):
    try:
        r = requests.get(url, headers={"X-RapidAPI-Key":KEY,"X-RapidAPI-Host":host}, params=params, timeout=20)
        d = r.json()
        its = d.get("data",{}).get("itineraries",[])
        out.append(f"{label}:{r.status_code} n={len(its)}")
        for it in its[:2]:
            legs=it.get("legs",[])
            out.append(f"  ILS{it.get('price',{}).get('raw')} stops={legs[0].get('stopCount',0) if legs else 0} airline={(legs[0].get('carriers',{}).get('marketing') or [{}])[0].get('name','?') if legs else '?'}")
        if not its: out.append(f"  {str(d)[:250]}")
    except Exception as e: out.append(f"{label} ERR:{e}")

test_api("Crawlio", "https://skyscanner-flights.p.rapidapi.com/v1/flights/search-one-way",
    "skyscanner-flights.p.rapidapi.com",
    {"origin":"TLV","destination":"ATH","date":dep,"adults":"1","currency":"ILS","countryCode":"IL","locale":"he-IL"})

test_api("ElisLab", "https://skyscanner-flights-travel-api.p.rapidapi.com/flights/searchFlights",
    "skyscanner-flights-travel-api.p.rapidapi.com",
    {"originSkyId":"TLV","destinationSkyId":"ATH","originEntityId":"95673529",
     "destinationEntityId":"95673481","date":dep,"adults":"1","currency":"ILS","locale":"he-IL","market":"IL","cabinClass":"economy","sortBy":"best","limit":"5"})

try:
    def get_id(iata):
        r=requests.get("https://flights-sky.p.rapidapi.com/flights/auto-complete",
            headers={"X-RapidAPI-Key":KEY,"X-RapidAPI-Host":"flights-sky.p.rapidapi.com"},
            params={"query":iata,"locale":"en-US"},timeout=10)
        places=r.json().get("data",[])
        for p in places:
            fp=p.get("navigation",{}).get("relevantFlightParams",{})
            if fp.get("skyId")==iata: return fp.get("entityId","")
        return places[0].get("navigation",{}).get("relevantFlightParams",{}).get("entityId","") if places else ""
    tlv_id=get_id("TLV"); ath_id=get_id("ATH")
    out.append(f"FlightsSky IDs: TLV={tlv_id} ATH={ath_id}")
    if tlv_id and ath_id:
        test_api("FlightsSky","https://flights-sky.p.rapidapi.com/flights/search-one-way",
            "flights-sky.p.rapidapi.com",
            {"fromEntityId":tlv_id,"toEntityId":ath_id,"departDate":dep,"adults":"1","currency":"ILS","locale":"he-IL","market":"IL"})
except Exception as e: out.append(f"FlightsSky ERR:{e}")

result="\n".join(out); print(result)
if PAT:
    sha_r=requests.get(f"https://api.github.com/repos/{REPO}/contents/DIAG.md",headers=GH)
    sha=sha_r.json().get("sha","") if sha_r.status_code==200 else ""
    rw=requests.put(f"https://api.github.com/repos/{REPO}/contents/DIAG.md",
        headers={**GH,"Content-Type":"application/json"},
        json={"message":"diag","content":base64.b64encode(result.encode()).decode(),"sha":sha,"branch":"main"})
    print(f"DIAG.md written: HTTP {rw.status_code}")
else:
    print("No PAT - cannot write DIAG.md")
