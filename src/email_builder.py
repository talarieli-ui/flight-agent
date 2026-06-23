"""
email_builder.py – בונה מייל HTML לדוח טיסות
כולל שאלת focus ו-reply handler
"""

from datetime import datetime

BEST_BOOKING_TIPS = {
    "general": "מחקרים מראים שהזמנה 6–8 שבועות מראש נותנת את המחיר הטוב ביותר לרוב היעדים.",
    "best_days_to_book": ["שלישי", "רביעי"],
    "best_days_to_fly": ["שלישי", "רביעי", "שבת"],
    "best_time_to_search": "00:00–06:00 (לילה) — מחירים מתעדכנים בלילה ולרוב זולים יותר בבוקר מוקדם.",
    "kayak_tip": "השתמש ב-Kayak Explore לחיפוש יעדים זולים בטווח תאריכים גמיש.",
    "wizz_tip": "Wizz Air מוציאה מבצעים ביום שלישי בצהריים. עקוב אחרי הניוזלטר.",
    "skyscanner_tip": "Skyscanner – השתמש ב-'כל החודש' כדי למצוא את היום הזול ביותר.",
    "hopper_tip": "Hopper חוזה מחירים עתידיים — הפעל Price Freeze לנעילת מחיר.",
    "momondo_tip": "Momondo מציגה לוח מחירים חודשי ב-Cheapest Month — מצוין לגמישות.",
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

def _fmt_dur(m):
    if not m: return "—"
    h, mn = divmod(m, 60)
    return f"{h}ש'{mn}ד'" if mn else f"{h}ש'"

def _fmt_date(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z",""))
        days = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
        months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                  "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
        return f"{days[dt.weekday()]}, {dt.day} {months[dt.month]}"
    except:
        return s[:10] if s else "—"

def _row(f, rank):
    code   = f.get("destination","?")
    flag   = DEST_FLAGS.get(code,"✈️")
    name   = f.get("dest_name", code)
    price  = f.get("price_ils", 0)
    color  = _price_color(price)
    dep    = _fmt_date(f.get("departure",""))
    dur    = _fmt_dur(f.get("duration_min",0))
    stops  = f.get("stops",0)
    s_str  = "ישיר ✈️" if stops==0 else f"{stops} עצירה"
    src    = f.get("source","—")
    link   = f.get("deep_link","#")
    win    = f.get("window_label","")
    rk_bg  = "#ffd700" if rank==1 else "#e2e8f0"
    rk_col = "#92400e" if rank==1 else "#475569"
    airline= f.get("airline","—")
    return f"""
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:10px 6px;text-align:center;">
        <span style="background:{rk_bg};color:{rk_col};border-radius:50%;width:26px;height:26px;
          display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;">{rank}</span>
      </td>
      <td style="padding:10px 6px;text-align:center;font-size:18px;">{flag}</td>
      <td style="padding:10px 6px;">
        <div style="font-weight:700;font-size:14px;color:#1e293b;">{name}</div>
        <div style="font-size:11px;color:#94a3b8;">{code} · {win}</div>
      </td>
      <td style="padding:10px 6px;text-align:center;">
        <span style="background:{color};color:#fff;padding:4px 10px;border-radius:20px;font-weight:700;font-size:13px;">₪{price:,}</span>
      </td>
      <td style="padding:10px 6px;text-align:center;color:#475569;font-size:12px;">{dep}</td>
      <td style="padding:10px 6px;text-align:center;color:#475569;font-size:12px;">{dur}</td>
      <td style="padding:10px 6px;text-align:center;color:#475569;font-size:12px;">{s_str}</td>
      <td style="padding:10px 6px;text-align:center;color:#64748b;font-size:11px;">{airline}</td>
      <td style="padding:10px 6px;text-align:center;">
        <a href="{link}" style="background:#3b82f6;color:#fff;padding:5px 12px;border-radius:6px;
          text-decoration:none;font-size:11px;font-weight:600;">הזמן ↗</a>
        <div style="font-size:9px;color:#94a3b8;margin-top:2px;">{src}</div>
      </td>
    </tr>"""

def _focus_section(reply_to_email: str) -> str:
    """
    Interactive focus section — user replies to the email with a destination.
    The subject line convention: 'FOCUS: <city/country>'
    """
    return f"""
    <tr><td style="padding:16px 0 8px;">
      <div style="background:linear-gradient(135deg,#1e40af,#7c3aed);border-radius:12px;padding:24px;color:#fff;">
        <div style="font-size:22px;margin-bottom:8px;">🎯 רוצה חיפוש ממוקד?</div>
        <p style="margin:0 0 16px;color:#c7d2fe;font-size:14px;line-height:1.6;">
          האם יש <strong>מדינה, עיר, או יעד ספציפי</strong> שתרצה שנסרוק במיוחד עבורך?<br/>
          שלח לנו מייל חוזר עם שם היעד ונשלח לך דוח מחירים מיידי!
        </p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20לונדון&body=אנא%20סרוק%20טיסות%20ללונדון"
             style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;
             text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">
            ✈️ לונדון
          </a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20פריז&body=אנא%20סרוק%20טיסות%20לפריז"
             style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;
             text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">
            🇫🇷 פריז
          </a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20ברצלונה&body=אנא%20סרוק%20טיסות%20לברצלונה"
             style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;
             text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">
            🇪🇸 ברצלונה
          </a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20בנגקוק&body=אנא%20סרוק%20טיסות%20לבנגקוק"
             style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;
             text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">
            🇹🇭 בנגקוק
          </a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20ניו+יורק&body=אנא%20סרוק%20טיסות%20לניו%20יורק"
             style="background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;
             text-decoration:none;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.3);">
            🇺🇸 ניו יורק
          </a>
          <a href="mailto:{reply_to_email}?subject=FOCUS%3A%20יעד+אחר&body=כתוב%20את%20שם%20היעד%20כאן"
             style="background:#fff;color:#3b82f6;padding:8px 16px;border-radius:8px;
             text-decoration:none;font-size:13px;font-weight:700;">
            ✏️ יעד אחר...
          </a>
        </div>
        <p style="margin:12px 0 0;color:#a5b4fc;font-size:11px;">
          שלח מייל עם subject: <code style="background:rgba(0,0,0,.3);padding:2px 6px;border-radius:4px;">FOCUS: שם היעד</code>
          · תקבל תשובה תוך דקות
        </p>
      </div>
    </td></tr>"""


def build_email_html(
    deals: list[dict],
    session: str = "morning",
    total_scanned: int = 0,
    focus_query: str = "",
    reply_to: str = "",
) -> str:
    now_he = datetime.now().strftime("%d/%m/%Y %H:%M")
    session_label = "🌅 בוקר טוב" if session == "morning" else "🌙 ערב טוב"
    tips = BEST_BOOKING_TIPS
    book_days = "יום " + " או יום ".join(tips["best_days_to_book"])
    fly_days  = "יום " + ", יום ".join(tips["best_days_to_fly"])

    focus_header = ""
    if focus_query:
        focus_header = f"""
        <tr><td style="padding:0 0 12px;">
          <div style="background:#fef3c7;border:2px solid #f59e0b;border-radius:10px;padding:12px 16px;
               color:#92400e;font-size:14px;font-weight:600;">
            🔍 דוח ממוקד עבור: <strong>{focus_query}</strong>
          </div>
        </td></tr>"""

    rows = "".join(_row(f, i+1) for i, f in enumerate(deals[:20]))
    if not rows:
        rows = '<tr><td colspan="9" style="padding:32px;text-align:center;color:#94a3b8;">לא נמצאו טיסות זמינות כרגע</td></tr>'

    reply_section = _focus_section(reply_to or "tal.arieli@gmail.com") if not focus_query else ""

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>דוח טיסות ✈️</title></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;direction:rtl;">

<table width="100%" cellpadding="0" cellspacing="0"
  style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);">
  <tr><td style="padding:28px 24px;text-align:center;">
    <div style="font-size:40px;margin-bottom:6px;">✈️</div>
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;">דוח טיסות יומי מישראל</h1>
    <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px;">
      {session_label} | {now_he} | נסרקו {total_scanned:,} טיסות
    </p>
  </td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="max-width:820px;margin:0 auto;padding:0 12px;">

  {focus_header}

  <tr><td style="padding:20px 0 6px;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 12px;">🏆 עסקאות הטיסות הטובות ביותר</h2>
    <div style="background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <thead>
          <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">#</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">🌍</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:right;">יעד</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">מחיר</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">תאריך</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">משך</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">עצירות</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">חברה</th>
            <th style="padding:10px 6px;font-size:11px;color:#94a3b8;text-align:center;">הזמנה</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </td></tr>

  {reply_section}

  <tr><td style="padding:14px 0 6px;">
    <h2 style="color:#1e293b;font-size:17px;margin:0 0 10px;">💡 מתי הכי כדאי להזמין?</h2>
    <div style="background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:18px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="width:50%;padding:0 10px 0 0;vertical-align:top;">
            <div style="background:#f0fdf4;border-right:4px solid #16a34a;padding:10px;border-radius:8px;margin-bottom:10px;">
              <div style="font-weight:700;color:#15803d;font-size:12px;margin-bottom:3px;">📅 ימי הזמנה מומלצים</div>
              <div style="color:#166534;font-size:13px;">{book_days}</div>
            </div>
            <div style="background:#eff6ff;border-right:4px solid #2563eb;padding:10px;border-radius:8px;margin-bottom:10px;">
              <div style="font-weight:700;color:#1d4ed8;font-size:12px;margin-bottom:3px;">✈️ ימי טיסה זולים</div>
              <div style="color:#1e40af;font-size:13px;">{fly_days}</div>
            </div>
            <div style="background:#fef9c3;border-right:4px solid #ca8a04;padding:10px;border-radius:8px;">
              <div style="font-weight:700;color:#92400e;font-size:12px;margin-bottom:3px;">🌙 שעת חיפוש מיטבית</div>
              <div style="color:#78350f;font-size:13px;">{tips["best_time_to_search"]}</div>
            </div>
          </td>
          <td style="width:50%;padding:0 0 0 10px;vertical-align:top;">
            <div style="background:#fdf4ff;border-right:4px solid #a855f7;padding:10px;border-radius:8px;margin-bottom:10px;">
              <div style="font-weight:700;color:#7e22ce;font-size:12px;margin-bottom:3px;">🗓️ כמה מראש?</div>
              <div style="color:#6b21a8;font-size:12px;">{tips["general"]}</div>
            </div>
            <div style="background:#fff7ed;border-right:4px solid #ea580c;padding:10px;border-radius:8px;margin-bottom:10px;">
              <div style="font-weight:700;color:#c2410c;font-size:12px;margin-bottom:3px;">🐰 Hopper</div>
              <div style="color:#9a3412;font-size:12px;">{tips["hopper_tip"]}</div>
            </div>
            <div style="background:#f0f9ff;border-right:4px solid #0284c7;padding:10px;border-radius:8px;">
              <div style="font-weight:700;color:#0369a1;font-size:12px;margin-bottom:3px;">🌊 Momondo</div>
              <div style="color:#075985;font-size:12px;">{tips["momondo_tip"]}</div>
            </div>
          </td>
        </tr>
      </table>
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
    <a href="https://www.cheapflights.com/flights-to/anywhere/?origin=TLV" style="background:#fd7c2a;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Cheapflights</a>
    <a href="https://www.easyjet.com/en" style="background:#ff6600;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">easyJet</a>
    <a href="https://www.ryanair.com/en/cheap-flights/from/tel-aviv" style="background:#073590;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">Ryanair</a>
    <a href="https://www.lastminute.com/flights/from-TLV/" style="background:#e10600;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;margin:3px;display:inline-block;">lastminute</a>
  </td></tr>

</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b;">
  <tr><td style="padding:18px 24px;text-align:center;">
    <p style="color:#64748b;font-size:11px;margin:0;">
      ✉️ Flight Scanner Agent · {now_he} · המחירים משתנים בזמן אמת
    </p>
  </td></tr>
</table>
</body></html>"""
