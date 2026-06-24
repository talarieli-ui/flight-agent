"""Email builder v8: round-trip prices, each flight clearly labeled, sorted low→high."""
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


def _build_flight_row(flight, rank, links):
    """One row per flight option: airline + price + book buttons."""
    price       = flight["price_ils"]
    airline     = flight.get("airline", "?")
    stops       = flight.get("transfers", 0)
    stops_lbl   = "ישיר ✅" if stops == 0 else f"{stops} עצירות"
    color       = _price_color(price)
    rank_bg     = "#fde047" if rank == 1 else "#f1f5f9"
    rank_color  = "#854d0e" if rank == 1 else "#475569"
    rank_text   = "🏆 הזול" if rank == 1 else f"#{rank}"

    return f"""
    <tr>
      <td style="padding:10px;border-bottom:1px solid #e2e8f0;width:65px;text-align:center;">
        <span style="background:{rank_bg};color:{rank_color};padding:3px 8px;border-radius:10px;font-size:10px;font-weight:700;white-space:nowrap;">{rank_text}</span>
      </td>
      <td style="padding:10px;border-bottom:1px solid #e2e8f0;color:#1e293b;font-size:13px;">
        <strong>{airline}</strong><br/>
        <span style="font-size:11px;color:#64748b;">{stops_lbl}</span>
      </td>
      <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:left;">
        <span style="background:{color};color:#fff;padding:5px 14px;border-radius:14px;font-weight:800;font-size:15px;white-space:nowrap;">₪{price:,}</span>
        <div style="font-size:9px;color:#94a3b8;margin-top:3px;">הלוך-חזור</div>
      </td>
      <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:left;white-space:nowrap;">
        <a href="{links['Skyscanner']}" target="_blank" rel="noopener" style="background:#00b2e3;color:#fff;padding:5px 10px;border-radius:5px;text-decoration:none;font-size:10px;font-weight:700;margin:2px;display:inline-block;">Skyscanner</a>
        <a href="{links['Google Flights']}" target="_blank" rel="noopener" style="background:#4285f4;color:#fff;padding:5px 10px;border-radius:5px;text-decoration:none;font-size:10px;font-weight:700;margin:2px;display:inline-block;">Google</a>
        <a href="{links['Kiwi.com']}" target="_blank" rel="noopener" style="background:#6366f1;color:#fff;padding:5px 10px;border-radius:5px;text-decoration:none;font-size:10px;font-weight:700;margin:2px;display:inline-block;">Kiwi</a>
      </td>
    </tr>"""


def _build_window_card(w):
    dep_str = _hebrew_date(w["dep"])
    ret_str = _hebrew_date(w["ret"])
    days    = (datetime.strptime(w["ret"],"%Y-%m-%d") - datetime.strptime(w["dep"],"%Y-%m-%d")).days
    flights = w.get("flights", [])
    links   = w.get("links", {})

    if not flights:
        body = """<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:10px;color:#92400e;font-size:12px;text-align:center;">
                ⚠️ אין מחיר מאומת לחלון זה — לחץ על אחד הכפתורים לחיפוש בזמן אמת
              </div>"""
    else:
        rows = "".join(_build_flight_row(f, i+1, links) for i, f in enumerate(flights))
        body = f"""
        <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-top:8px;">
          <thead>
            <tr style="background:#f8fafc;">
              <th style="padding:8px 10px;text-align:right;font-size:10px;color:#64748b;">דירוג</th>
              <th style="padding:8px 10px;text-align:right;font-size:10px;color:#64748b;">חברה</th>
              <th style="padding:8px 10px;text-align:left;font-size:10px;color:#64748b;">מחיר</th>
              <th style="padding:8px 10px;text-align:left;font-size:10px;color:#64748b;">חיפוש באתרים</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    extra_btns = f"""
        <div style="margin-top:8px;font-size:11px;color:#64748b;">
          חיפוש נוסף:
          <a href="{links.get('Wizz Air','#')}" target="_blank" style="background:#c6007e;color:#fff;padding:4px 9px;border-radius:5px;text-decoration:none;font-size:10px;font-weight:700;margin:0 3px;display:inline-block;">Wizz</a>
          <a href="{links.get('Kayak','#')}" target="_blank" style="background:#ff690f;color:#fff;padding:4px 9px;border-radius:5px;text-decoration:none;font-size:10px;font-weight:700;margin:0 3px;display:inline-block;">Kayak</a>
          <a href="{links.get('Aviasales','#')}" target="_blank" style="background:#ff5722;color:#fff;padding:4px 9px;border-radius:5px;text-decoration:none;font-size:10px;font-weight:700;margin:0 3px;display:inline-block;">Aviasales</a>
        </div>"""

    return f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin:10px 0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;">
        <div style="font-size:14px;color:#1e293b;font-weight:700;">
          {w["icon"]} {w["label"]} <span style="color:#94a3b8;font-size:11px;font-weight:400;">({days} ימים)</span>
        </div>
      </div>
      <div style="font-size:12px;color:#475569;margin-bottom:4px;">
        <strong>הלוך:</strong> {dep_str} &nbsp;•&nbsp; <strong>חזור:</strong> {ret_str}
      </div>
      {body}
      {extra_btns}
    </div>"""


def _build_destination_card(dest, rank=None):
    flag   = dest.get("flag","✈️")
    code   = dest["code"]
    name   = dest["name"]
    best_p = dest.get("best_price_ils")

    if best_p:
        color = _price_color(best_p)
        price_badge = f"""<span style="background:{color};color:#fff;padding:5px 14px;border-radius:20px;font-weight:800;font-size:15px;">החל מ-₪{best_p:,} הלוך-חזור</span>"""
        rank_badge = f"""<span style="background:#fde047;color:#854d0e;border-radius:50%;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;margin-left:8px;">{rank}</span>""" if rank else ""
    else:
        price_badge = """<span style="background:#f1f5f9;color:#64748b;padding:4px 12px;border-radius:14px;font-size:12px;font-weight:600;">⏱️ לחץ לחיפוש בזמן אמת</span>"""
        rank_badge  = ""

    windows_html = "".join(_build_window_card(w) for w in dest["windows"])

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
    calls_made   = hub_data.get("calls_made", 0)

    cards_html = ""
    rank = 1
    for d in destinations:
        cards_html += _build_destination_card(d, rank=rank if d.get("best_price_ils") else None)
        if d.get("best_price_ils"):
            rank += 1

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>מחירי טיסה הלוך-חזור ✈️</title></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;direction:rtl;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);">
  <tr><td style="padding:28px 24px;text-align:center;">
    <div style="font-size:42px;margin-bottom:6px;">✈️</div>
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;">מחירי טיסה הלוך-חזור</h1>
    <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px;">
      {session_label} | {now_he} | {n_priced}/{n_total} יעדים | quota: {quota_left}
    </p>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="max-width:920px;margin:0 auto;padding:0 12px;">
  <tr><td style="padding:14px 0;">
    <div style="background:#f0fdf4;border:1px solid #16a34a;border-radius:10px;padding:14px 18px;">
      <div style="color:#166534;font-size:14px;font-weight:700;margin-bottom:6px;">
        ✅ מחירי הלוך-חזור אמיתיים מ-Google Flights
      </div>
      <div style="color:#15803d;font-size:13px;line-height:1.7;">
        כל מחיר = מחיר הטיסה <strong>הלוך-חזור</strong> כפי שמופיע ב-Google Flights באותו רגע.<br/>
        לחיצה על כפתור Skyscanner / Google / Kiwi → ייפתח האתר <strong>עם התאריכים והיעד מולאים מראש</strong>.<br/>
        צבעים: <span style="color:#16a34a;font-weight:700;">ירוק &lt; ₪800</span> ·
        <span style="color:#2563eb;font-weight:700;">כחול &lt; ₪1,500</span> ·
        <span style="color:#d97706;font-weight:700;">כתום &lt; ₪2,500</span> ·
        <span style="color:#dc2626;font-weight:700;">אדום &gt; ₪2,500</span>.
      </div>
    </div>
  </td></tr>

  <tr><td>{cards_html}</td></tr>

  <tr><td style="padding:14px 0 8px;text-align:center;">
    <h2 style="color:#1e293b;font-size:16px;margin:0 0 10px;">🇮🇱 אתרים ישראלים</h2>
    <a href="https://flyall.club/Flights" target="_blank" style="background:#0066cc;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">FlyAll</a>
    <a href="https://www.maxtravel.co.il/" target="_blank" style="background:#e31e24;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">MaxTravel</a>
    <a href="https://www.hulyo.co.il/flights" target="_blank" style="background:#ff6b35;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">חוליו</a>
    <a href="https://secretflights.co.il/last-minute-flights/" target="_blank" style="background:#1a1a2e;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">טיסות סודיות</a>
    <a href="https://www.kishrey-teufa.co.il/flights" target="_blank" style="background:#6b21a8;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">קשרי תעופה</a>
    <a href="https://www.issta.co.il/Flights" target="_blank" style="background:#0070b8;color:#fff;padding:7px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">איסתא</a>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b;">
  <tr><td style="padding:18px 24px;text-align:center;">
    <p style="color:#64748b;font-size:11px;margin:0;">
      ✉️ Flight Scanner v8 · הלוך-חזור · {now_he} · {calls_made} API calls
    </p>
  </td></tr>
</table>
</body></html>"""
