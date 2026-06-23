"""
Email builder for the Search Hub strategy.
Builds a Hebrew RTL email organized by category with date windows.
"""
from datetime import datetime


def _hebrew_date(date_str):
    """Format YYYY-MM-DD as Hebrew weekday + day month."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return date_str
    days   = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
    months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
              "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    return f"יום {days[dt.weekday()]} {dt.day} {months[dt.month]}"


def _site_btn(name, url, bg, fg="#fff"):
    return (
        f'<a href="{url}" target="_blank" rel="noopener" '
        f'style="background:{bg};color:{fg};padding:7px 12px;border-radius:6px;'
        f'text-decoration:none;font-size:12px;font-weight:600;margin:2px;display:inline-block;">'
        f'{name}</a>'
    )


def _build_destination_card(dest):
    """Render one destination with all its date windows."""
    flag = dest.get("flag", "✈️")
    code = dest["code"]
    name = dest["name"]

    windows_html = ""
    for w in dest["windows"]:
        dep_str = _hebrew_date(w["dep"])
        ret_str = _hebrew_date(w["ret"])
        days    = (datetime.strptime(w["ret"], "%Y-%m-%d") - datetime.strptime(w["dep"], "%Y-%m-%d")).days

        # Site buttons row
        btns = (
            _site_btn("🔎 Skyscanner",  w["links"]["Skyscanner"],     "#00b2e3") +
            _site_btn("Google",         w["links"]["Google Flights"], "#4285f4") +
            _site_btn("Kiwi",           w["links"]["Kiwi.com"],       "#00a991") +
            _site_btn("Wizz",           w["links"]["Wizz Air"],       "#c6007e") +
            _site_btn("Kayak",          w["links"]["Kayak"],          "#ff690f") +
            _site_btn("Aviasales",      w["links"]["Aviasales"],      "#ff5722")
        )

        windows_html += f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin:8px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div>
              <span style="font-size:13px;color:#1e293b;font-weight:700;">{w["icon"]} {w["label"]}</span>
              <span style="color:#94a3b8;font-size:11px;margin-right:6px;">({days} ימים)</span>
            </div>
          </div>
          <div style="font-size:12px;color:#475569;margin-bottom:8px;">
            <strong>הלוך:</strong> {dep_str} &nbsp;•&nbsp;
            <strong>חזור:</strong> {ret_str}
          </div>
          <div style="margin-top:8px;">{btns}</div>
        </div>
        """

    return f"""
    <div style="background:#f8fafc;border-radius:12px;padding:16px;margin:12px 0;border-right:4px solid #3b82f6;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h3 style="margin:0;color:#1e293b;font-size:17px;font-weight:700;">
          {flag} {name} <span style="color:#94a3b8;font-size:13px;font-weight:400;">({code})</span>
        </h3>
      </div>
      {windows_html}
    </div>
    """


def _build_section(title, icon, destinations):
    if not destinations:
        return ""
    cards = "".join(_build_destination_card(d) for d in destinations)
    return f"""
    <tr><td style="padding:16px 0 8px;">
      <h2 style="color:#1e293b;font-size:18px;margin:0 0 8px;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">
        {icon} {title}
      </h2>
      {cards}
    </td></tr>
    """


def build_email_html(hub_data, session="morning", focus_query="", reply_to=""):
    now_he = datetime.now().strftime("%d/%m/%Y %H:%M")
    session_label = "🌅 בוקר טוב" if session == "morning" else "🌙 ערב טוב"

    destinations = hub_data.get("destinations", [])
    n_dest       = len(destinations)
    n_windows    = sum(len(d.get("windows", [])) for d in destinations)

    # Group by category
    greek  = [d for d in destinations if d.get("category") == "greek"]
    europe = [d for d in destinations if d.get("category") == "europe"]
    asia   = [d for d in destinations if d.get("category") == "asia"]
    usa    = [d for d in destinations if d.get("category") == "usa"]

    sections = (
        _build_section("איי יוון ויעדים יווניים", "🏝️", greek) +
        _build_section("אירופה",                  "🌍", europe) +
        _build_section("אסיה ומזרח תיכון",        "🌏", asia) +
        _build_section("ארה\"ב",                  "🇺🇸", usa)
    )

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

<!-- Header -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);">
  <tr><td style="padding:28px 24px;text-align:center;">
    <div style="font-size:42px;margin-bottom:6px;">✈️</div>
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;">מרכז חיפוש טיסות</h1>
    <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px;">
      {session_label} | {now_he} | {n_dest} יעדים × {n_windows} חלונות תאריכים
    </p>
  </td></tr>
</table>

<!-- Intro banner -->
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:900px;margin:0 auto;padding:0 12px;">
  <tr><td style="padding:14px 0;">
    <div style="background:#f0fdf4;border:1px solid #16a34a;border-radius:10px;padding:14px 18px;">
      <div style="color:#166534;font-size:14px;font-weight:700;margin-bottom:6px;">
        ✅ מחירים אמיתיים בלבד — לא מציגים מחירים מבלי לוודא
      </div>
      <div style="color:#15803d;font-size:13px;line-height:1.6;">
        לכל יעד תמצא כפתורי חיפוש לאתרים המובילים. 
        כל לחיצה פותחת את אתר ההזמנה <strong>עם התאריך והיעד מולאים מראש</strong> — 
        שם תראה את המחיר המעודכן ביותר.
      </div>
    </div>
  </td></tr>

  {focus_header}

  {sections}

  <!-- Israeli agencies row -->
  <tr><td style="padding:16px 0 8px;text-align:center;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 10px;">🇮🇱 חיפוש כללי - אתרים ישראלים</h2>
    <a href="https://flyall.club/Flights" target="_blank" style="background:#0066cc;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">FlyAll</a>
    <a href="https://www.maxtravel.co.il/deals/%D7%98%D7%99%D7%A1%D7%95%D7%AA-%D7%94%D7%A8%D7%92%D7%A2-%D7%94%D7%90%D7%97%D7%A8%D7%95%D7%9F" target="_blank" style="background:#e31e24;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">MaxTravel</a>
    <a href="https://www.hulyo.co.il/flights" target="_blank" style="background:#ff6b35;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">⚡ חוליו</a>
    <a href="https://secretflights.co.il/last-minute-flights/" target="_blank" style="background:#1a1a2e;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🔒 טיסות סודיות</a>
    <a href="https://www.kishrey-teufa.co.il/flights" target="_blank" style="background:#6b21a8;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">קשרי תעופה</a>
    <a href="https://www.issta.co.il/Flights" target="_blank" style="background:#0070b8;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">איסתא</a>
    <a href="https://www.ophirtours.co.il/flights.html" target="_blank" style="background:#be7206;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">אופיר טורס</a>
  </td></tr>

  <!-- Direct airlines -->
  <tr><td style="padding:8px 0;text-align:center;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 10px;">✈️ הזמנה ישירה מחברות תעופה</h2>
    <a href="https://www.elal.com/he-il/israel" target="_blank" style="background:#003399;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 אל על</a>
    <a href="https://www.israir.co.il/Flights/FlightSearch" target="_blank" style="background:#003087;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 ישראייר</a>
    <a href="https://www.arkia.com/he/flights" target="_blank" style="background:#e8000d;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇮🇱 ארקיע</a>
    <a href="https://booking.bluebirdair.com/BOOK/outbound" target="_blank" style="background:#1a6eb5;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🐦 Bluebird</a>
    <a href="https://en.aegeanair.com/flights/?origin=TLV" target="_blank" style="background:#002f6c;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇬🇷 Aegean</a>
    <a href="https://www.skyexpress.gr/en/flights/?from=TLV" target="_blank" style="background:#0099cc;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">🇬🇷 Sky Express</a>
  </td></tr>

  <!-- Facebook groups -->
  <tr><td style="padding:8px 0 22px;text-align:center;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 10px;">👥 קבוצות פייסבוק</h2>
    <a href="https://www.facebook.com/groups/natkati" target="_blank" style="background:#1877f2;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">נתקעתי ברגע האחרון</a>
    <a href="https://www.facebook.com/SecretFlights.co.il" target="_blank" style="background:#1877f2;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">טיסות סודיות</a>
    <a href="https://www.facebook.com/Hulyo.il" target="_blank" style="background:#1877f2;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">חוליו</a>
  </td></tr>

</table>

<!-- Footer -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b;">
  <tr><td style="padding:18px 24px;text-align:center;">
    <p style="color:#64748b;font-size:11px;margin:0;">
      ✉️ Flight Scanner Agent · {now_he} · מרכז חיפוש - מחירים אמיתיים בלבד
    </p>
  </td></tr>
</table>
</body></html>"""
