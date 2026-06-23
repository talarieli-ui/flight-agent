"""
email_builder.py – מייל HTML לדוח טיסות
- מציג: תאריך+שעת המראה הלוך, תאריך+שעת המראה חזור
- ממוין לפי מחיר מהנמוך לגבוה
- טיסות ישירות בלבד
"""

from datetime import datetime

BEST_BOOKING_TIPS = {
    "best_days_to_book": ["שלישי", "רביעי"],
    "best_days_to_fly":  ["שלישי", "רביעי", "שבת"],
    "best_time_to_search": "00:00–06:00 — מחירים מתעדכנים בלילה.",
    "general":     "הזמנה 6–8 שבועות מראש = המחיר הטוב ביותר לרוב היעדים.",
    "wizz_tip":    "Wizz Air: מבצעים ביום שלישי בצהריים.",
    "hopper_tip":  "Hopper חוזה מחירים עתידיים — Price Freeze לנעילת מחיר.",
    "momondo_tip": "Momondo: לוח Cheapest Month למציאת היום הזול.",
}

DEST_FLAGS = {
    "LHR":"🇬🇧","CDG":"🇫🇷","FCO":"🇮🇹","BCN":"🇪🇸","AMS":"🇳🇱",
    "VIE":"🇦🇹","PRG":"🇨🇿","BUD":"🇭🇺","ATH":"🇬🇷","DUB":"🇮🇪",
    "LIS":"🇵🇹","MXP":"🇮🇹","MAD":"🇪🇸","WAW":"🇵🇱","BER":"🇩🇪",
    "MUC":"🇩🇪","CPH":"🇩🇰","ARN":"🇸🇪","OSL":"🇳🇴","HEL":"🇫🇮",
    "ZRH":"🇨🇭","GVA":"🇨🇭","BRU":"🇧🇪","SKG":"🇬🇷","HER":"🇬🇷",
    "OTP":"🇷🇴","SOF":"🇧🇬","JFK":"🇺🇸","LAX":"🇺🇸","MIA":"🇺🇸",
    "ORD":"🇺🇸","YYZ":"🇨🇦","DXB":"🇦🇪","BKK":"🇹🇭","NRT":"🇯🇵",
    "SIN":"🇸🇬","HKG":"🇭🇰","ICN":"🇰🇷","DEL":"🇮🇳","BOM":"🇮🇳",
    "CAI":"🇪🇬","CMN":"🇲🇦","CPT":"🇿🇦","NBO":"🇰🇪",
}


def _price_color(p):
    if p < 1500: return "#16a34a"
    if p < 3000: return "#2563eb"
    if p < 6000: return "#d97706"
    return "#dc2626"


def _fmt_datetime(s: str) -> tuple:
    """Returns (date_str, time_str) in Hebrew format."""
    if not s or len(s) < 10:
        return "—", "—"
    try:
        dt = datetime.fromisoformat(s.replace("Z", ""))
        days   = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
        months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                  "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
        date_s = f"{days[dt.weekday()]} {dt.day} {months[dt.month]}"
        time_s = dt.strftime("%H:%M")
        return date_s, time_s
    except Exception:
        return s[:10], ""


def build_deep_link(source: str, origin: str, dest_code: str, departure_date: str) -> str:
    try:
        dt = datetime.strptime(departure_date[:10], "%Y-%m-%d")
    except Exception:
        dt = datetime.now()
    d8 = dt.strftime("%Y%m%d")
    dy = dt.strftime("%Y-%m-%d")
    # All links are pre-filled with origin, destination, and exact departure date
    links = {
        "Kiwi.com": (
            f"https://www.kiwi.com/en/search/results/"
            f"tel-aviv-israel/{dest_code.lower()}-airport/{dy}/{dy}"
            f"?adults=1&cabinClass=ECONOMY&directOnly=true"
        ),
        "Aviasales": (
            f"https://www.aviasales.com/search/{origin}{d8}{dest_code}1"
        ),
        "Jetradar": (
            f"https://www.jetradar.com/flights/{origin}-{dest_code}/{dy}/?adults=1&direct=true"
        ),
        "Google Flights": (
            f"https://www.google.com/travel/flights/search"
            f"?tfs=CBwQARoeEgoyMDI2LTA3LTEwagcIARIDVExWcgcIARIDTEhS"
            f"&q=direct+flights+from+TLV+to+{dest_code}+on+{dy}"
        ),
        "FlyAll": (
            f"https://flyall.club/Flights"
            f"?origin={origin}&destination={dest_code}&departDate={dy}&adults=1&direct=true"
        ),
        "MaxTravel": (
            f"https://www.maxtravel.co.il/flights"
            f"?origin={origin}&destination={dest_code}&departureDate={dy}&adults=1&stops=0"
        ),
        "Hulyo": (
            f"https://www.hulyo.co.il/flights"
            f"?origin={origin}&dest={dest_code}&date={dy}&direct=1"
        ),
        "Expedia": (
            f"https://www.expedia.com/Flights-Search"
            f"?trip=oneway&leg1=from%3A{origin}%2Cto%3A{dest_code}%2Cdeparture%3A{d8}TANYT"
            f"&passengers=adults%3A1&options=cabinclass%3Aeconomy%2Cnopenalty%3AN%2Cmaxhops%3A0"
        ),
        "eDreams": (
            f"https://www.edreams.com/flights/#{origin}-{dest_code}/{dy}/1adults/0inf/0children/economy/0/0/false/0"
        ),
        "Skyscanner": (
            f"https://www.skyscanner.net/transport/flights"
            f"/{origin.lower()}/{dest_code.lower()}/{d8}/"
            f"?adults=1&cabinclass=economy&stops=!oneStop,!twoPlusStops"
        ),
    }
    # Default to Skyscanner with pre-filled params
    return links.get(source, links["Skyscanner"])


def _row(f: dict, rank: int) -> str:
    code    = f.get("destination", "?")
    flag    = DEST_FLAGS.get(code, "✈️")
    name    = f.get("dest_name", code)
    price   = f.get("price_ils", 0)
    color   = _price_color(price)
    airline = f.get("airline", "—")
    src     = f.get("source", "—")
    origin  = f.get("origin", "TLV")

    # Outbound
    dep_date, dep_time = _fmt_datetime(f.get("departure", ""))
    arr_date, arr_time = _fmt_datetime(f.get("arrival", ""))

    # Return (inbound) — may be empty if not available
    ret_dep_date, ret_dep_time = _fmt_datetime(f.get("return_departure", ""))
    ret_arr_date, ret_arr_time = _fmt_datetime(f.get("return_arrival", ""))

    dep_str  = f.get("departure", "")
    dep_date = dep_str[:10] if dep_str else ""
    # Always build a pre-filled deep link — override any stored empty link
    link = build_deep_link(src, origin, code, dep_date) if dep_date else "#"

    # Price alert: RED ring for < ₪500, GOLD for rank 1, default grey
    price_val = f.get("price_ils", 99999)
    if price_val < 500:
        rk_bg  = "#ef4444"   # אדום — מתחת ל-₪500
        rk_col = "#fff"
    elif rank == 1:
        rk_bg  = "#ffd700"   # זהב — מקום ראשון
        rk_col = "#92400e"
    else:
        rk_bg  = "#e2e8f0"
        rk_col = "#475569"

    # Format outbound cell
    outbound_cell = f"""
        <div style="font-weight:600;color:#1e293b;font-size:13px;">{dep_date}</div>
        <div style="color:#3b82f6;font-size:13px;font-weight:700;">{dep_time} ✈</div>
        {"<div style='font-size:11px;color:#94a3b8;'>נחיתה: "+arr_date+" "+arr_time+"</div>" if arr_time and arr_time != "—" else ""}
    """

    # Format return cell
    if ret_dep_date and ret_dep_date != "—":
        return_cell = f"""
            <div style="font-weight:600;color:#1e293b;font-size:13px;">{ret_dep_date}</div>
            <div style="color:#7c3aed;font-size:13px;font-weight:700;">{ret_dep_time} ✈</div>
            {"<div style='font-size:11px;color:#94a3b8;'>נחיתה: "+ret_arr_date+" "+ret_arr_time+"</div>" if ret_arr_time and ret_arr_time != "—" else ""}
        """
    else:
        return_cell = '<div style="color:#94a3b8;font-size:11px;">חד-כיווני</div>'

    return f"""
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:10px 6px;text-align:center;vertical-align:middle;">
        <span style="background:{rk_bg};color:{rk_col};border-radius:50%;width:26px;height:26px;
          display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;">{rank}</span>
      </td>
      <td style="padding:10px 6px;text-align:center;font-size:20px;vertical-align:middle;">{flag}</td>
      <td style="padding:10px 6px;vertical-align:middle;">
        <div style="font-weight:700;font-size:14px;color:#1e293b;">{name}</div>
        <div style="font-size:11px;color:#94a3b8;">{code} · {airline}</div>
        <div style="font-size:10px;color:#cbd5e1;margin-top:2px;">{src}</div>
      </td>
      <td style="padding:10px 6px;text-align:center;vertical-align:middle;">
        <span style="background:{color};color:#fff;padding:5px 12px;border-radius:20px;font-weight:700;font-size:14px;white-space:nowrap;">₪{price:,}</span>
        <div style="font-size:10px;color:#94a3b8;margin-top:3px;">ישיר ✅</div>
      </td>
      <td style="padding:10px 8px;vertical-align:middle;text-align:right;">{outbound_cell}</td>
      <td style="padding:10px 8px;vertical-align:middle;text-align:right;">{return_cell}</td>
      <td style="padding:10px 6px;text-align:center;vertical-align:middle;">
        <a href="{link}" target="_blank" rel="noopener"
           style="background:#3b82f6;color:#fff;padding:7px 14px;border-radius:8px;
           text-decoration:none;font-size:12px;font-weight:700;white-space:nowrap;">הזמן ↗</a>
      </td>
    </tr>"""


def _focus_section(reply_to_email: str) -> str:
    return f"""
    <tr><td style="padding:16px 0 8px;">
      <div style="background:linear-gradient(135deg,#1e40af,#7c3aed);border-radius:12px;padding:24px;color:#fff;">
        <div style="font-size:22px;margin-bottom:8px;">🎯 רוצה חיפוש ממוקד?</div>
        <p style="margin:0 0 16px;color:#c7d2fe;font-size:14px;line-height:1.6;">
          יש <strong>מדינה, עיר, או יעד ספציפי</strong> שתרצה שנסרוק במיוחד?<br/>
          שלח מייל חוזר עם שם היעד ותקבל דוח מחירים מיידי!
        </p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20לונדון" style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">✈️ לונדון</a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20פריז" style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">🇫🇷 פריז</a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20ברצלונה" style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">🇪🇸 ברצלונה</a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20בנגקוק" style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">🇹🇭 בנגקוק</a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20יעד+אחר" style="background:#fff;color:#3b82f6;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:700;">✏️ יעד אחר...</a>
        </div>
        <p style="margin:12px 0 0;color:#a5b4fc;font-size:11px;">subject: <code style="background:rgba(0,0,0,.3);padding:2px 6px;border-radius:4px;">FOCUS: שם היעד</code></p>
      </div>
    </td></tr>"""


def build_email_html(
    deals: list,
    session: str = "morning",
    total_scanned: int = 0,
    focus_query: str = "",
    reply_to: str = "",
) -> str:
    now_he = datetime.now().strftime("%d/%m/%Y %H:%M")
    session_label = "🌅 בוקר טוב" if session == "morning" else "🌙 ערב טוב"
    tips = BEST_BOOKING_TIPS

    # Sort by price ascending (direct only guaranteed by scanner)
    deals_sorted = sorted(deals, key=lambda x: x.get("price_ils", 99999))

    focus_header = ""
    if focus_query:
        focus_header = f"""<tr><td style="padding:0 0 12px;">
          <div style="background:#fef3c7;border:2px solid #f59e0b;border-radius:10px;padding:12px 16px;color:#92400e;font-size:14px;font-weight:600;">
            🔍 דוח ממוקד: <strong>{focus_query}</strong>
          </div></td></tr>"""

    rows = "".join(_row(f, i+1) for i, f in enumerate(deals_sorted[:20]))
    if not rows:
        rows = '<tr><td colspan="7" style="padding:32px;text-align:center;color:#94a3b8;">לא נמצאו טיסות ישירות זמינות</td></tr>'

    reply_section = _focus_section(reply_to or "tal.arieli@gmail.com") if not focus_query else ""
    book_days = "יום " + " או יום ".join(tips["best_days_to_book"])
    fly_days  = "יום " + ", יום ".join(tips["best_days_to_fly"])

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>דוח טיסות ✈️</title></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;direction:rtl;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);">
  <tr><td style="padding:28px 24px;text-align:center;">
    <div style="font-size:40px;margin-bottom:6px;">✈️</div>
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;">דוח טיסות ישירות מישראל</h1>
    <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px;">
      {session_label} | {now_he} | {total_scanned:,} טיסות נסרקו | ישירות בלבד ✅
    </p>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="max-width:900px;margin:0 auto;padding:0 12px;">

  {focus_header}

  <tr><td style="padding:20px 0 6px;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 4px;">🏆 הטיסות הישירות הזולות ביותר</h2>
    <div style="display:flex;gap:12px;margin:0 0 12px;align-items:center;flex-wrap:wrap;">
      <span style="font-size:12px;color:#64748b;">ממוין לפי מחיר ↑ | טווח חיפוש: 3 ימים–6 חודשים</span>
      <span style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;">🔴 מתחת ל-₪500</span>
      <span style="background:#ffd700;color:#92400e;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;">🏆 הזול ביותר</span>
    </div>
    <div style="background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <thead>
          <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">#</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">🌍</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:right;">יעד / חברה</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">מחיר ↑</th>
            <th style="padding:10px 6px;font-size:11px;color:#3b82f6;text-align:right;">✈️ הלוך</th>
            <th style="padding:10px 6px;font-size:11px;color:#7c3aed;text-align:right;">✈️ חזור</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">הזמנה</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p style="color:#94a3b8;font-size:10px;margin:6px 0 0;text-align:right;">
      * "הזמן ↗" פותח את אתר ההזמנה עם התאריך והיעד מולאים מראש
    </p>
  </td></tr>

  {reply_section}

  <tr><td style="padding:14px 0 6px;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 10px;">💡 מתי הכי כדאי להזמין?</h2>
    <div style="background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:18px;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="width:50%;padding:0 10px 0 0;vertical-align:top;">
          <div style="background:#f0fdf4;border-right:4px solid #16a34a;padding:10px;border-radius:8px;margin-bottom:10px;">
            <div style="font-weight:700;color:#15803d;font-size:12px;margin-bottom:3px;">📅 ימי הזמנה מומלצים</div>
            <div style="color:#166534;font-size:13px;">{book_days}</div>
          </div>
          <div style="background:#eff6ff;border-right:4px solid #2563eb;padding:10px;border-radius:8px;">
            <div style="font-weight:700;color:#1d4ed8;font-size:12px;margin-bottom:3px;">✈️ ימי טיסה זולים</div>
            <div style="color:#1e40af;font-size:13px;">{fly_days}</div>
          </div>
        </td>
        <td style="width:50%;padding:0 0 0 10px;vertical-align:top;">
          <div style="background:#fef9c3;border-right:4px solid #ca8a04;padding:10px;border-radius:8px;margin-bottom:10px;">
            <div style="font-weight:700;color:#92400e;font-size:12px;margin-bottom:3px;">🌙 שעת חיפוש מיטבית</div>
            <div style="color:#78350f;font-size:13px;">{tips["best_time_to_search"]}</div>
          </div>
          <div style="background:#fdf4ff;border-right:4px solid #a855f7;padding:10px;border-radius:8px;">
            <div style="font-weight:700;color:#7e22ce;font-size:12px;margin-bottom:3px;">🗓️ כמה מראש?</div>
            <div style="color:#6b21a8;font-size:12px;">{tips["general"]}</div>
          </div>
        </td>
      </tr></table>
    </div>
  </td></tr>

  <tr><td style="padding:14px 0 22px;text-align:center;">
    <p style="color:#94a3b8;font-size:11px;margin:0 0 10px;">חיפוש מהיר</p>
    <a href="https://www.skyscanner.net/routes/tlv/anywhere/" style="background:#00b2e3;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Skyscanner</a>
    <a href="https://www.kayak.com/explore/TLV" style="background:#ff690f;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Kayak</a>
    <a href="https://www.wizzair.com/#/booking/select-flight/TLV/" style="background:#c6007e;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Wizz Air</a>
    <a href="https://www.google.com/flights?hl=iw#flt=TLV.." style="background:#4285f4;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Google Flights</a>
    <a href="https://www.kiwi.com/en/search/results/tel-aviv-israel/anywhere/" style="background:#e74c3c;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Kiwi.com</a>
    <a href="https://www.hopper.com/" style="background:#6e45e2;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🐰 Hopper</a>
    <a href="https://www.momondo.com/flight-search/Tel-Aviv/Anywhere" style="background:#005580;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Momondo</a>
    <a href="https://www.jetradar.com/flights/TLV-/" style="background:#1a9b6c;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Jetradar</a>
    <a href="https://www.ryanair.com/en/cheap-flights/from/tel-aviv" style="background:#073590;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Ryanair</a>
    <a href="https://www.expedia.com/Flights-Search?trip=oneway&leg1=from%3ATLV%2Cto%3Aanywhere&passengers=adults%3A1&options=cabinclass%3Aeconomy%2Cmaxhops%3A0" style="background:#ffcc00;color:#000;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Expedia</a>
    <a href="https://www.edreams.com/flights/#TLV/anywhere/1adults/0inf/0children/economy" style="background:#0073e6;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">eDreams</a>
    <a href="https://www.walla-tours.co.il/catalog/flights?origin=TLV" style="background:#cc0000;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">וואלה טורס</a>
  </td></tr>

  <tr><td style="padding:8px 0 6px;text-align:center;">
    <p style="color:#94a3b8;font-size:11px;margin:0 0 10px;">🇮🇱 ישראלים + חברות תעופה ישירות</p>
    <a href="https://flyall.club/Flights" style="background:#0066cc;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">✈️ FlyAll</a>
    <a href="https://www.maxtravel.co.il/deals/%D7%98%D7%99%D7%A1%D7%95%D7%AA-%D7%94%D7%A8%D7%92%D7%A2-%D7%94%D7%90%D7%97%D7%A8%D7%95%D7%9F" style="background:#e31e24;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">💳 MaxTravel</a>
    <a href="https://www.hulyo.co.il/flights" style="background:#ff6b35;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">⚡ חוליו</a>
    <a href="https://secretflights.co.il/last-minute-flights/" style="background:#1a1a2e;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🔒 טיסות סודיות</a>
    <a href="https://www.israir.co.il/Flights/FlightSearch" style="background:#003087;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 ישראייר</a>
    <a href="https://www.arkia.com/he/flights" style="background:#e8000d;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 ארקיע</a>
    <a href="https://www.elal.com/he-il/israel" style="background:#003399;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 אל על</a>
  </td></tr>

  <tr><td style="padding:4px 0 22px;text-align:center;">
    <p style="color:#94a3b8;font-size:11px;margin:0 0 10px;">👥 קבוצות פייסבוק ישראליות</p>
    <a href="https://www.facebook.com/groups/natkati" style="background:#1877f2;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">נתקעתי ברגע האחרון</a>
    <a href="https://www.facebook.com/SecretFlights.co.il" style="background:#1877f2;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">טיסות סודיות</a>
    <a href="https://www.facebook.com/Hulyo.il" style="background:#1877f2;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">חוליו</a>
  </td></tr>

</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b;">
  <tr><td style="padding:18px 24px;text-align:center;">
    <p style="color:#64748b;font-size:11px;margin:0;">
      ✉️ Flight Scanner Agent · {now_he} · ישירות בלבד · 3 ימים–6 חודשים קדימה
    </p>
  </td></tr>
</table>
</body></html>"""
