"""Email builder v4: hub + real prices, sorted by best price."""
from datetime import datetime


def _hebrew_date(date_str):
    try: dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except: return date_str
    days   = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
    months = ["","ינו'","פבר'","מרץ","אפר'","מאי","יוני","יולי","אוג'","ספט'","אוק'","נוב'","דצמ'"]
    return f"יום {days[dt.weekday()]} {dt.day} {months[dt.month]}"


def _price_color(p):
    if p < 800:  return "#16a34a"   # green
    if p < 1500: return "#2563eb"   # blue
    if p < 2500: return "#d97706"   # orange
    return "#dc2626"                # red


def _site_btn(name, url, bg, fg="#fff"):
    return (f'<a href="{url}" target="_blank" rel="noopener" '
            f'style="background:{bg};color:{fg};padding:6px 11px;border-radius:6px;'
            f'text-decoration:none;font-size:11px;font-weight:600;margin:2px;display:inline-block;">'
            f'{name}</a>')


def _build_destination_card(dest, rank=None):
    flag        = dest.get("flag","✈️")
    code        = dest["code"]
    name        = dest["name"]
    best_price  = dest.get("best_price")
    best_window = dest.get("best_window_label", "")

    # Price badge in header
    if best_price:
        price_ils = best_price["price_ils"]
        color     = _price_color(price_ils)
        stops     = best_price.get("transfers", 0)
        stops_lbl = "ישיר ✅" if stops == 0 else f"{stops} עצירות"
        match_dt  = _hebrew_date(best_price.get("match_date", ""))
        airline   = best_price.get("airline", "?")
        price_badge = f"""
        <div style="display:flex;align-items:center;gap:10px;background:#f0fdf4;
                    border:1px solid #16a34a;border-radius:8px;padding:8px 12px;margin:8px 0;">
          <span style="background:{color};color:#fff;padding:5px 14px;border-radius:20px;
                       font-weight:800;font-size:16px;">₪{price_ils:,}</span>
          <span style="font-size:12px;color:#166534;">
            <strong>הזול ביותר</strong> · {stops_lbl} · {airline}<br/>
            <span style="color:#15803d;">{match_dt} · {best_window}</span>
          </span>
        </div>"""
        rank_badge = f"""<span style="background:#fde047;color:#854d0e;border-radius:50%;
                       width:28px;height:28px;display:inline-flex;align-items:center;
                       justify-content:center;font-weight:800;font-size:13px;
                       margin-left:8px;">{rank}</span>""" if rank else ""
    else:
        price_badge = """
        <div style="background:#f1f5f9;border:1px dashed #cbd5e1;border-radius:8px;
                    padding:8px 12px;margin:8px 0;color:#64748b;font-size:12px;">
          💡 מחיר לא במטמון — לחץ על אחד הכפתורים למטה לחיפוש בזמן אמת
        </div>"""
        rank_badge = ""

    # Windows
    windows_html = ""
    for w in dest["windows"]:
        dep_str = _hebrew_date(w["dep"])
        ret_str = _hebrew_date(w["ret"])
        days    = (datetime.strptime(w["ret"],"%Y-%m-%d") - datetime.strptime(w["dep"],"%Y-%m-%d")).days

        wp = w.get("price")
        if wp:
            price_label = f'<span style="background:{_price_color(wp["price_ils"])};color:#fff;padding:3px 10px;border-radius:20px;font-weight:700;font-size:12px;">₪{wp["price_ils"]:,}</span>'
            stops_lbl = "ישיר ✅" if wp.get("transfers",0)==0 else f"{wp.get('transfers')} עצירות"
            price_line = f'<div style="font-size:11px;color:#475569;margin-top:4px;">{stops_lbl} · {wp.get("airline","?")}</div>'
        else:
            price_label = '<span style="color:#94a3b8;font-size:11px;">⏱️ לחץ לחיפוש</span>'
            price_line = ""

        btns = (
            _site_btn("🔎 Skyscanner", w["links"]["Skyscanner"],     "#00b2e3") +
            _site_btn("Google",         w["links"]["Google Flights"], "#4285f4") +
            _site_btn("Kiwi",           w["links"]["Kiwi.com"],       "#00a991") +
            _site_btn("Wizz",           w["links"]["Wizz Air"],       "#c6007e") +
            _site_btn("Kayak",          w["links"]["Kayak"],          "#ff690f") +
            _site_btn("Aviasales",      w["links"]["Aviasales"],      "#ff5722")
        )

        windows_html += f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:11px;margin:7px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div style="font-size:13px;color:#1e293b;font-weight:700;">{w["icon"]} {w["label"]}
              <span style="color:#94a3b8;font-size:11px;font-weight:400;">({days} ימים)</span>
            </div>
            <div>{price_label}</div>
          </div>
          <div style="font-size:12px;color:#475569;">
            <strong>הלוך:</strong> {dep_str} &nbsp;•&nbsp; <strong>חזור:</strong> {ret_str}
          </div>
          {price_line}
          <div style="margin-top:7px;">{btns}</div>
        </div>"""

    return f"""
    <div style="background:#f8fafc;border-radius:12px;padding:14px 16px;margin:10px 0;
                border-right:4px solid {'#16a34a' if best_price else '#94a3b8'};">
      <h3 style="margin:0 0 4px;color:#1e293b;font-size:17px;font-weight:700;">
        {rank_badge}{flag} {name} <span style="color:#94a3b8;font-size:13px;font-weight:400;">({code})</span>
      </h3>
      {price_badge}
      {windows_html}
    </div>"""


def _build_section(title, icon, destinations, base_rank=0):
    if not destinations: return ""
    cards = ""
    for i, d in enumerate(destinations):
        rank = base_rank + i + 1 if d.get("best_price") else None
        cards += _build_destination_card(d, rank=rank)
    return f"""
    <tr><td style="padding:14px 0 6px;">
      <h2 style="color:#1e293b;font-size:18px;margin:0 0 8px;
                 border-bottom:2px solid #e2e8f0;padding-bottom:6px;">
        {icon} {title}
      </h2>
      {cards}
    </td></tr>"""


def build_email_html(hub_data, session="morning", focus_query="", reply_to=""):
    now_he = datetime.now().strftime("%d/%m/%Y %H:%M")
    session_label = "🌅 בוקר טוב" if session == "morning" else "🌙 ערב טוב"

    destinations = hub_data.get("destinations", [])
    n_priced     = hub_data.get("n_priced", 0)
    n_total      = hub_data.get("n_total", len(destinations))

    # Already sorted globally by price (priced first, then unpriced) by scanner
    # But re-group by category preserving order
    greek_priced  = [d for d in destinations if d.get("category")=="greek" and d.get("best_price")]
    greek_unp     = [d for d in destinations if d.get("category")=="greek" and not d.get("best_price")]
    europe_priced = [d for d in destinations if d.get("category")=="europe" and d.get("best_price")]
    europe_unp    = [d for d in destinations if d.get("category")=="europe" and not d.get("best_price")]
    asia_priced   = [d for d in destinations if d.get("category")=="asia" and d.get("best_price")]
    asia_unp      = [d for d in destinations if d.get("category")=="asia" and not d.get("best_price")]
    usa_priced    = [d for d in destinations if d.get("category")=="usa" and d.get("best_price")]
    usa_unp       = [d for d in destinations if d.get("category")=="usa" and not d.get("best_price")]

    greek  = greek_priced + greek_unp
    europe = europe_priced + europe_unp
    asia   = asia_priced + asia_unp
    usa    = usa_priced + usa_unp

    rank = 0
    sec_greek = _build_section("איי יוון ויעדים יווניים", "🏝️", greek, rank); rank += len(greek_priced)
    sec_eu    = _build_section("אירופה",                  "🌍", europe, rank); rank += len(europe_priced)
    sec_asia  = _build_section("אסיה ומזרח תיכון",        "🌏", asia, rank); rank += len(asia_priced)
    sec_usa   = _build_section('ארה"ב',                   "🇺🇸", usa, rank)

    focus_header = ""
    if focus_query:
        focus_header = f"""<tr><td style="padding:0 0 12px;">
          <div style="background:#fef3c7;border:2px solid #f59e0b;border-radius:10px;padding:12px 16px;color:#92400e;font-size:14px;font-weight:600;">
            🔍 חיפוש ממוקד: <strong>{focus_query}</strong>
          </div></td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>מרכז חיפוש טיסות ✈️</title></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;direction:rtl;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);">
  <tr><td style="padding:28px 24px;text-align:center;">
    <div style="font-size:42px;margin-bottom:6px;">✈️</div>
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;">מרכז חיפוש טיסות</h1>
    <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px;">
      {session_label} | {now_he} | {n_priced}/{n_total} יעדים עם מחיר מאומת | ממוין ↑
    </p>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="max-width:900px;margin:0 auto;padding:0 12px;">
  <tr><td style="padding:14px 0;">
    <div style="background:#f0fdf4;border:1px solid #16a34a;border-radius:10px;padding:14px 18px;">
      <div style="color:#166534;font-size:14px;font-weight:700;margin-bottom:6px;">
        ✅ מחירים אמיתיים בלבד · ממוין מהזול לגבוה
      </div>
      <div style="color:#15803d;font-size:13px;line-height:1.6;">
        מחירים <strong>ירוקים = פחות מ-₪800</strong> · 
        <strong style="color:#2563eb;">כחולים = פחות מ-₪1,500</strong> · 
        <strong style="color:#d97706;">כתומים = פחות מ-₪2,500</strong>.
        יעדים בלי מחיר מאומת מופיעים בסוף — לחץ על Skyscanner לראות מחיר אמיתי.
      </div>
    </div>
  </td></tr>

  {focus_header}
  {sec_greek}
  {sec_eu}
  {sec_asia}
  {sec_usa}

  <tr><td style="padding:14px 0 8px;text-align:center;">
    <h2 style="color:#1e293b;font-size:16px;margin:0 0 10px;">🇮🇱 חיפוש כללי - אתרים ישראלים</h2>
    <a href="https://flyall.club/Flights" target="_blank" style="background:#0066cc;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">FlyAll</a>
    <a href="https://www.maxtravel.co.il/deals/%D7%98%D7%99%D7%A1%D7%95%D7%AA-%D7%94%D7%A8%D7%92%D7%A2-%D7%94%D7%90%D7%97%D7%A8%D7%95%D7%9F" target="_blank" style="background:#e31e24;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">MaxTravel</a>
    <a href="https://www.hulyo.co.il/flights" target="_blank" style="background:#ff6b35;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">⚡ חוליו</a>
    <a href="https://secretflights.co.il/last-minute-flights/" target="_blank" style="background:#1a1a2e;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🔒 טיסות סודיות</a>
    <a href="https://www.kishrey-teufa.co.il/flights" target="_blank" style="background:#6b21a8;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">קשרי תעופה</a>
    <a href="https://www.issta.co.il/Flights" target="_blank" style="background:#0070b8;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">איסתא</a>
    <a href="https://www.ophirtours.co.il/flights.html" target="_blank" style="background:#be7206;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">אופיר טורס</a>
  </td></tr>

  <tr><td style="padding:8px 0;text-align:center;">
    <h2 style="color:#1e293b;font-size:16px;margin:0 0 10px;">✈️ חברות תעופה</h2>
    <a href="https://www.elal.com/he-il/israel" target="_blank" style="background:#003399;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 אל על</a>
    <a href="https://www.israir.co.il/Flights/FlightSearch" target="_blank" style="background:#003087;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 ישראייר</a>
    <a href="https://www.arkia.com/he/flights" target="_blank" style="background:#e8000d;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 ארקיע</a>
    <a href="https://booking.bluebirdair.com/BOOK/outbound" target="_blank" style="background:#1a6eb5;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🐦 Bluebird</a>
    <a href="https://en.aegeanair.com/flights/?origin=TLV" target="_blank" style="background:#002f6c;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇬🇷 Aegean</a>
    <a href="https://www.skyexpress.gr/en/flights/?from=TLV" target="_blank" style="background:#0099cc;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇬🇷 Sky Express</a>
  </td></tr>

  <tr><td style="padding:8px 0 22px;text-align:center;">
    <h2 style="color:#1e293b;font-size:16px;margin:0 0 10px;">👥 קבוצות פייסבוק</h2>
    <a href="https://www.facebook.com/groups/natkati" target="_blank" style="background:#1877f2;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">נתקעתי ברגע האחרון</a>
    <a href="https://www.facebook.com/SecretFlights.co.il" target="_blank" style="background:#1877f2;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">טיסות סודיות</a>
    <a href="https://www.facebook.com/Hulyo.il" target="_blank" style="background:#1877f2;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">חוליו</a>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b;">
  <tr><td style="padding:18px 24px;text-align:center;">
    <p style="color:#64748b;font-size:11px;margin:0;">
      ✉️ Flight Scanner v4 · {now_he} · מחירים אמיתיים בלבד · {n_priced}/{n_total} עם מחיר
    </p>
  </td></tr>
</table>
</body></html>"""
