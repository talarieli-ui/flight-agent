"""
main.py - Flight Scanner Agent
Real prices only. Sends debug info when no deals found.
"""
import os, smtplib, logging, urllib.request, json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SMTP_HOST        = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER        = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS", "tal.arieli@gmail.com,ker22ari@gmail.com").split(",")
SESSION          = os.environ.get("EMAIL_SESSION", "morning")
FOCUS_QUERY      = os.environ.get("FOCUS_QUERY", "").strip()
SENDGRID_KEY     = os.environ.get("SENDGRID_API_KEY", "")
RAPIDAPI_KEY     = os.environ.get("RAPIDAPI_KEY", "")
SERPAPI_KEY      = os.environ.get("SERPAPI_KEY", "")


def send_via_smtp(subject, html_body, recipients):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Flight Scanner <{SMTP_USER}>"
    msg["To"]      = ", ".join(recipients)
    msg["Reply-To"] = SMTP_USER
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as srv:
            srv.ehlo(); srv.starttls(); srv.ehlo()
            srv.login(SMTP_USER, SMTP_PASSWORD)
            srv.sendmail(SMTP_USER, recipients, msg.as_bytes())
        logger.info(f"Sent to {recipients}"); return True
    except Exception as e:
        logger.error(f"SMTP: {e}"); return False


def build_debug_email(raw_count, deals_count, api_status):
    """Build a debug email showing what APIs returned."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rows = "".join(f"<tr><td style=\"padding:8px;border-bottom:1px solid #eee;\">{k}</td><td style=\"padding:8px;border-bottom:1px solid #eee;\">{v}</td></tr>" for k,v in api_status.items())
    return f"""<!DOCTYPE html><html lang="he" dir="rtl">
<head><meta charset="UTF-8"/></head>
<body style="font-family:Arial,sans-serif;direction:rtl;padding:20px;">
<h2 style="color:#1e40af;">✈️ דוח טיסות {now}</h2>
<div style="background:#fef3c7;border:2px solid #f59e0b;border-radius:8px;padding:16px;margin-bottom:16px;">
  <strong>⚠️ לא נמצאו טיסות עומדות בקריטריונים</strong><br/>
  סרוקו: {raw_count} תוצאות גולמיות → {deals_count} עסקאות תקפות מתחת ל-₪3,500
</div>
<h3>סטטוס APIs:</h3>
<table style="border-collapse:collapse;width:100%;">
<thead><tr style="background:#f8fafc;"><th style="padding:8px;text-align:right;">API</th><th style="padding:8px;text-align:right;">תוצאה</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p style="color:#64748b;font-size:12px;margin-top:20px;">בדוק את GitHub Actions logs לפרטים נוספים.</p>
</body></html>"""


def main():
    logger.info(f"Starting | session={SESSION}")
    logger.info(f"RAPIDAPI_KEY: {len(RAPIDAPI_KEY)} chars")
    logger.info(f"SERPAPI_KEY: {len(SERPAPI_KEY)} chars")
    logger.info(f"SMTP_USER: {SMTP_USER}")

    from flight_scanner import (scan_all_flights, scan_focused, find_best_deals,
                                 SkyscannerCrawlio, SkyscannerElisLab, FlightsScraperSky,
                                 SerpAPIFlights, AviasalesScraper)

    # Quick API status check on one route
    api_status = {}
    test_dest = "ATH"; test_date = "2026-07-10"

    c = SkyscannerCrawlio()
    res = c.search("TLV", test_dest, test_date)
    api_status[f"Crawlio (TLV→{test_dest})"] = f"✅ {len(res)} results" if res else f"❌ 0 results (ok={c._ok})"

    e = SkyscannerElisLab()
    res2 = e.search("TLV", test_dest, test_date)
    api_status[f"ElisLab (TLV→{test_dest})"] = f"✅ {len(res2)} results" if res2 else f"❌ 0 results (ok={e._ok})"

    sk = FlightsScraperSky()
    res3 = sk.search("TLV", test_dest, test_date)
    api_status[f"FlightsSky (TLV→{test_dest})"] = f"✅ {len(res3)} results" if res3 else f"❌ 0 results (ok={sk._ok})"

    s = SerpAPIFlights()
    res4 = s.search("TLV", test_dest, test_date)
    api_status[f"SerpAPI (TLV→{test_dest})"] = f"✅ {len(res4)} results" if res4 else f"❌ 0 results (ok={s._ok})"

    av = AviasalesScraper()
    res5 = av.search("TLV", test_dest, test_date)
    api_status[f"Aviasales (TLV→{test_dest})"] = f"✅ {len(res5)} results" if res5 else f"❌ 0 results"

    logger.info(f"API test results: {api_status}")

    # Full scan
    raw   = scan_focused(FOCUS_QUERY) if SESSION == "focus" and FOCUS_QUERY else scan_all_flights()
    deals = find_best_deals(raw, top_n=20)
    total = len(raw)

    logger.info(f"Raw: {total} | Deals ≤₪3500: {len(deals)}")

    now = datetime.now()
    if deals:
        from email_builder import build_email_html
        html = build_email_html(deals=deals, session=SESSION, total_scanned=total,
                                focus_query=FOCUS_QUERY if SESSION=="focus" else "",
                                reply_to=SMTP_USER)
        top_price = deals[0]["price_ils"]; top_dest = deals[0]["dest_name"]
        subject = f"✈️ טיסות ישירות {now.strftime('%d/%m/%Y')} | הזול: ₪{top_price:,} ל{top_dest}"
    else:
        html    = build_debug_email(total, len(deals), api_status)
        subject = f"✈️ דוח טיסות {now.strftime('%d/%m/%Y')} | 0 תוצאות — ראה פרטי API"

    if not send_via_smtp(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
