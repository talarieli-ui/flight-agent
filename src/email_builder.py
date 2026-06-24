"""Email builder v7: per-OTA price tables. Each row = real OTA name + that OTA's price."""
from datetime import datetime


def _hebrew_date(date_str):
    try: dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except: return date_str
    days   = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
    months = ["","ינו'","פבר'","מרץ","אפר'","מאי","יוני","יולי","אוג'","ספט'","אוק'","נוב'","דצמ'"]
    return f"יום {days[dt.weekday()]} {dt.day} {months[dt.month]}"


def _price_color(p):
    if p < 800:  return "#16a34a"
    if p < 1500: return "#2563eb"
    if p < 2500: return "#d97706"
    return "#dc2626"


def _ota_url(ota_name, fallback_url, dest_links):
    """Map an OTA name to the best matching site link."""
    ota_lower = ota_name.lower()
    if fallback_url:
        return fallback_url
    if "skyscanner" in ota_lower:    return dest_links.get("Skyscanner","#")
    if "kiwi"       in ota_lower:    return dest_links.get("Kiwi.com","#")
    if "wizz"       in ota_lower:    return dest_links.get("Wizz Air","#")
    if "kayak"      in ota_lower:    return dest_links.get("Kayak","#")
    if "aviasales"  in ota_lower:    return dest_links.get("Aviasales","#")
    if "google"     in ota_lower:    return dest_links.get("Google Flights","#")
    return dest_links.get("Google Flights","#")


def _build_ota_table(ota_prices, dest_links):
    """A clean rows-style price table: OTA name | price | book button."""
    if not ota_prices:
        return """<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:10px;color:#92400e;font-size:12px;">
                  ⚠️ לא נמצא מחיר מאומת לחלון התאריכים הזה</div>"""

    rows = ""
    for i, p in enumerate(ota_prices):
        ota   = p["ota"]
        price = p["price_ils"]
        url   = _ota_url(ota, p.get("url",""), dest_links)
        color = _price_color(price)
        rank_color = "#fde047" if i == 0 else "#f1f5f9"
        rank_text  = "🏆 הזול" if i == 0 else f"#{i+1}"

        rows += f"""
        <tr>
          <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;width:60px;text-align:center;">
            <span style="background:{rank_color};color:{'#854d0e' if i==0 else '#475569'};padding:3px 8px;border-radius:10px;font-size:10px;font-weight:700;">{rank_text}</span>
          </td>
          <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#1e293b;font-size:13px;">
            {ota}
          </td>
          <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:left;">
            <span style="background:{color};color:#fff;padding:4px 12px;border-radius:14px;font-weight:800;font-size:14px;">₪{price:,}</span>
          </td>
          <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:left;">
            <a href="{url}" target="_blank" rel="noopener" style="background:#1e40af;color:#fff;padding:5px 12px;border-radius:5px;text-decoration:none;font-size:11px;font-weight:700;">להזמין ←</a>
          </td>
        </tr>"""

    return f"""
    <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-top:6px;">
      <thead>
        <tr style="background:#f8fafc;">
          <th style="padding:8px 10px;text-align:right;font-size:11px;color:#64748b;">דירוג</th>
          <th style="padding:8px 10px;text-align:right;font-size:11px;color:#64748b;">אתר</th>
          <th style="padding:8px 10px;text-align:left;font-size:11px;color:#64748b;">מחיר</th>
          <th style="padding:8px 10px;text-align:left;font-size:11px;color:#64748b;">פעולה</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _build_destination_card(dest, rank=None):
    flag   = dest.get("flag","✈️")
    code   = dest["code"]
    name   = dest["name"]
    best_p = dest.get("best_price_ils")

    if best_p:
        color = _price_color(best_p)
        price_badge = f"""<span style="background:{color};color:#fff;padding:5px 14px;border-radius:20px;font-weight:800;font-size:15px;margin-right:8px;">החל מ-₪{best_p:,}</span>"""
        rank_badge = f"""<span style="background:#fde047;color:#854d0e;border-radius:50%;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;margin-left:8px;">{rank}</span>""" if rank else ""
    else:
        price_badge = """<span style="background:#f1f5f9;color:#64748b;padding:4px 12px;border-radius:14px;font-size:12px;font-weight:600;">⏱️ לחץ לחיפוש בזמן אמת</span>"""
        rank_badge  = ""

    windows_html = ""
    for w in dest["windows"]:
        dep_str = _hebrew_date(w["dep"])
        ret_str = _hebrew_date(w["ret"])
        days    = (datetime.strptime(w["ret"],"%Y-%m-%d") - datetime.strptime(w["dep"],"%Y-%m-%d")).days
        meta    = w.get("flight_meta") or {}
        airline = meta.get("airline","?") if meta else "?"
        stops   = meta.get("transfers", 0) if meta else 0
        stops_lbl = "ישיר ✅" if stops == 0 else f"{stops} עצירות"

        ota_table = _build_ota_table(w.get("ota_prices", []), w.get("links", {}))

        windows_html += f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin:10px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;">
            <div style="font-size:14px;color:#1e293b;font-weight:700;">
              {w["icon"]} {w["label"]} <span style="color:#94a3b8;font-size:11px;font-weight:400;">({days} ימים)</span>
            </div>
            {'<div style="font-size:11px;color:#64748b;">✈️ ' + airline + ' · ' + stops_lbl + '</div>' if meta else ''}
          </div>
          <div style="font-size:12px;color:#475569;margin-bottom:4px;">
            <strong>הלוך:</strong> {dep_str} &nbsp;•&nbsp; <strong>חזור:</strong> {ret_str}
          </div>
          {ota_table}
        </div>"""

    return f"""
    <div style="background:#f8fafc;border-radius:12px;padding:14px 16px;margin:10px 0;
                border-right:4px solid {'#16a34a' if best_p else '#94a3b8'};">
      <h3 style="margin:0 0 6px;color:#1e293b;font-size:17px;font-weight:700;">
        {rank_badge}{flag} {name} <span style="color:#94a3b8;font-size:13px;font-weight:400;">({code})</span>
      </h3>
      <div style="margin:8px 0;">{price_badge}</div>
      {windows_html}
    </div>"""


def build_email_html(hub_data, session="morning", focus_query="", reply_to=""):
    now_he = datetime.now().strftime("%d/%m/%Y %H:%M")
    session_label = "🌅 בוקר טוב" if session == "morning" else "🌙 ערב טוב"

    destinations = hub_data.get("destinations", [])
    n_priced     = hub_data.get("n_priced", 0)
    n_total      = hub_data.get("n_total", len(destinations))
    quota_left   = hub_data.get("quota_left", 0)

    cards_html = ""
    rank = 1
    for d in destinations:
        cards_html += _build_destination_card(d, rank=rank if d.get("best_price_ils") else None)
        if d.get("best_price_ils"):
            rank += 1

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>מחירי טיסה מאומתים ✈️</title></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;direction:rtl;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);">
  <tr><td style="padding:28px 24px;text-align:center;">
    <div style="font-size:42px;margin-bottom:6px;">✈️</div>
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;">מחירי טיסה מאומתים</h1>
    <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px;">
      {session_label} | {now_he} | {n_priced}/{n_total} יעדים | quota נותר: {quota_left}
    </p>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="max-width:920px;margin:0 auto;padding:0 12px;">
  <tr><td style="padding:14px 0;">
    <div style="background:#f0fdf4;border:1px solid #16a34a;border-radius:10px;padding:14px 18px;">
      <div style="color:#166534;font-size:14px;font-weight:700;margin-bottom:6px;">
        ✅ כל מחיר נלקח ישירות מאתר ההזמנה — לא משוערך, לא ממוצע
      </div>
      <div style="color:#15803d;font-size:13px;line-height:1.7;">
        לכל יעד וחלון תאריכים: טבלה עם <strong>שם האתר</strong> + <strong>המחיר המדויק</strong> שאותו אתר מציע + כפתור "להזמין".
        מסודר מהזול לגבוה. צבעים: <span style="color:#16a34a;font-weight:700;">ירוק &lt; ₪800</span>,
        <span style="color:#2563eb;font-weight:700;">כחול &lt; ₪1,500</span>,
        <span style="color:#d97706;font-weight:700;">כתום &lt; ₪2,500</span>,
        <span style="color:#dc2626;font-weight:700;">אדום &gt; ₪2,500</span>.
      </div>
    </div>
  </td></tr>

  <tr><td>{cards_html}</td></tr>

  <tr><td style="padding:14px 0 8px;text-align:center;">
    <h2 style="color:#1e293b;font-size:16px;margin:0 0 10px;">🇮🇱 אתרים ישראלים — חיפוש כללי</h2>
    <a href="https://flyall.club/Flights" target="_blank" style="background:#0066cc;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">FlyAll</a>
    <a href="https://www.maxtravel.co.il/deals/%D7%98%D7%99%D7%A1%D7%95%D7%AA-%D7%94%D7%A8%D7%92%D7%A2-%D7%94%D7%90%D7%97%D7%A8%D7%95%D7%9F" target="_blank" style="background:#e31e24;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">MaxTravel</a>
    <a href="https://www.hulyo.co.il/flights" target="_blank" style="background:#ff6b35;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">חוליו</a>
    <a href="https://secretflights.co.il/last-minute-flights/" target="_blank" style="background:#1a1a2e;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">טיסות סודיות</a>
    <a href="https://www.kishrey-teufa.co.il/flights" target="_blank" style="background:#6b21a8;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">קשרי תעופה</a>
    <a href="https://www.issta.co.il/Flights" target="_blank" style="background:#0070b8;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">איסתא</a>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b;">
  <tr><td style="padding:18px 24px;text-align:center;">
    <p style="color:#64748b;font-size:11px;margin:0;">
      ✉️ Flight Scanner v7 · {now_he} · {hub_data.get('calls_made',0)} API calls · quota left: {quota_left}
    </p>
  </td></tr>
</table>
</body></html>"""
