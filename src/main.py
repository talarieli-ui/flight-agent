"""
main.py - Flight Scanner Agent
Uses sendgrid or fallback SMTP for email delivery.
"""
import os
import smtplib
import logging
import urllib.request
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SMTP_USER        = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS", "tal.arieli@gmail.com,ker22ari@gmail.com").split(",")
SESSION          = os.environ.get("EMAIL_SESSION", "morning")
FOCUS_QUERY      = os.environ.get("FOCUS_QUERY", "").strip()
TEST_MODE        = os.environ.get("TEST_MODE", "false").lower() == "true"
SENDGRID_KEY     = os.environ.get("SENDGRID_API_KEY", "")

MOCK_DEALS = [
    {"destination": "BUD", "dest_name": "\u05d1\u05d5\u05d3\u05e4\u05e9\u05d8",  "price_ils": 890,  "departure": "2026-07-10T07:00:00", "duration_min": 195, "stops": 0, "airline": "Wizz Air",   "source": "Kiwi",           "deep_link": "https://wizzair.com",        "window_label": "\u05e9\u05d1\u05d5\u05e2\u05d9\u05d9\u05dd"},
    {"destination": "PRG", "dest_name": "\u05e4\u05e8\u05d0\u05d2",               "price_ils": 950,  "departure": "2026-07-12T09:00:00", "duration_min": 200, "stops": 0, "airline": "Wizz Air",   "source": "Kiwi",           "deep_link": "https://wizzair.com",        "window_label": "\u05e9\u05d1\u05d5\u05e2\u05d9\u05d9\u05dd"},
    {"destination": "ATH", "dest_name": "\u05d0\u05ea\u05d5\u05e0\u05d4",         "price_ils": 1050, "departure": "2026-07-18T10:00:00", "duration_min": 160, "stops": 0, "airline": "Aegean",     "source": "Aviasales",      "deep_link": "https://aviasales.com",      "window_label": "\u05d7\u05d5\u05d3\u05e9 \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "LHR", "dest_name": "\u05dc\u05d5\u05e0\u05d3\u05d5\u05df",   "price_ils": 1290, "departure": "2026-07-15T06:00:00", "duration_min": 280, "stops": 0, "airline": "EL AL",      "source": "Kiwi",           "deep_link": "https://kiwi.com",           "window_label": "\u05e9\u05dc\u05d5\u05e9\u05d4 \u05e9\u05d1\u05d5\u05e2\u05d5\u05ea"},
    {"destination": "VIE", "dest_name": "\u05d5\u05d9\u05e0\u05d4",               "price_ils": 1120, "departure": "2026-07-20T06:30:00", "duration_min": 220, "stops": 0, "airline": "Austrian",   "source": "Kiwi",           "deep_link": "https://kiwi.com",           "window_label": "\u05d7\u05d5\u05d3\u05e9 \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "BCN", "dest_name": "\u05d1\u05e8\u05e6\u05dc\u05d5\u05e0\u05d4","price_ils":1490,"departure":"2026-07-22T08:30:00","duration_min":310,"stops":0,"airline":"Vueling",  "source": "Aviasales",      "deep_link": "https://aviasales.com",      "window_label": "\u05d7\u05d5\u05d3\u05e9 \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "CDG", "dest_name": "\u05e4\u05e8\u05d9\u05d6",               "price_ils": 1550, "departure": "2026-07-25T07:00:00", "duration_min": 295, "stops": 0, "airline": "Air France","source": "Kiwi",           "deep_link": "https://kiwi.com",           "window_label": "\u05d7\u05d5\u05d3\u05e9 \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "DXB", "dest_name": "\u05d3\u05d5\u05d1\u05d0\u05d9",         "price_ils": 1380, "departure": "2026-08-01T02:00:00", "duration_min": 210, "stops": 0, "airline": "Emirates", "source": "Google Flights", "deep_link": "https://google.com/flights", "window_label": "\u05d7\u05d5\u05d3\u05e9\u05d9\u05d9\u05dd \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "MAD", "dest_name": "\u05de\u05d3\u05e8\u05d9\u05d3",         "price_ils": 1650, "departure": "2026-07-28T07:00:00", "duration_min": 330, "stops": 0, "airline": "Iberia",    "source": "Aviasales",      "deep_link": "https://aviasales.com",      "window_label": "\u05d7\u05d5\u05d3\u05e9 \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "BKK", "dest_name": "\u05d1\u05e0\u05d2\u05e7\u05d5\u05e7",   "price_ils": 2490, "departure": "2026-09-05T00:30:00", "duration_min": 660, "stops": 1, "airline": "Thai",      "source": "Kiwi",           "deep_link": "https://kiwi.com",           "window_label": "\u05e9\u05dc\u05d5\u05e9\u05d4 \u05d7\u05d5\u05d3\u05e9\u05d9\u05dd"},
    {"destination": "JFK", "dest_name": "\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7","price_ils":3200,"departure":"2026-08-10T22:00:00","duration_min":720,"stops":0,"airline":"Delta",    "source": "Google Flights", "deep_link": "https://google.com/flights", "window_label": "\u05d7\u05d5\u05d3\u05e9\u05d9\u05d9\u05dd \u05e7\u05d3\u05d9\u05de\u05d4"},
    {"destination": "LIS", "dest_name": "\u05dc\u05d9\u05e1\u05d1\u05d5\u05df",   "price_ils": 1720, "departure": "2026-08-05T06:00:00", "duration_min": 350, "stops": 0, "airline": "TAP",       "source": "Kiwi",           "deep_link": "https://kiwi.com",           "window_label": "\u05d7\u05d5\u05d3\u05e9\u05d9\u05d9\u05dd \u05e7\u05d3\u05d9\u05de\u05d4"},
]


def send_via_sendgrid(subject, html_body, recipients):
    """Send via SendGrid API (HTTP, no SMTP port needed)."""
    payload = json.dumps({
        "personalizations": [{"to": [{"email": r} for r in recipients]}],
        "from": {"email": SMTP_USER, "name": "Flight Scanner"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}]
    }).encode()
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            logger.info(f"SendGrid: HTTP {r.status}")
            return r.status in (200, 202)
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return False


def send_via_smtp(subject, html_body, recipients):
    """Send via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Flight Scanner <{SMTP_USER}>"
    msg["To"]      = ", ".join(recipients)
    msg["Reply-To"] = SMTP_USER
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as srv:
            srv.ehlo(); srv.starttls(); srv.ehlo()
            srv.login(SMTP_USER, SMTP_PASSWORD)
            srv.sendmail(SMTP_USER, recipients, msg.as_bytes())
        logger.info(f"SMTP: sent to {recipients}")
        return True
    except Exception as e:
        logger.error(f"SMTP error: {e}")
        return False


def send_email(subject, html_body, recipients):
    if SENDGRID_KEY:
        logger.info("Sending via SendGrid...")
        if send_via_sendgrid(subject, html_body, recipients):
            return True
        logger.warning("SendGrid failed, trying SMTP...")
    logger.info("Sending via SMTP...")
    return send_via_smtp(subject, html_body, recipients)


def main():
    logger.info(f"Starting | session={SESSION} | test={TEST_MODE}")
    logger.info(f"SMTP_USER: {'set' if SMTP_USER else 'MISSING'}")
    logger.info(f"SMTP_PASSWORD: {'set (' + str(len(SMTP_PASSWORD)) + ' chars)' if SMTP_PASSWORD else 'MISSING'}")
    logger.info(f"SENDGRID_KEY: {'set' if SENDGRID_KEY else 'not set'}")
    logger.info(f"Recipients: {RECIPIENT_EMAILS}")
    logger.info(f"TEST_MODE value: '{os.environ.get('TEST_MODE', 'NOT SET')}'")

    if TEST_MODE:
        logger.info("TEST MODE: using mock data")
        deals = MOCK_DEALS
        total = len(deals)
    else:
        from flight_scanner import scan_all_flights, scan_focused, find_best_deals
        is_focused = SESSION == "focus" and FOCUS_QUERY
        raw   = scan_focused(FOCUS_QUERY) if is_focused else scan_all_flights()
        deals = find_best_deals(raw, top_n=20)
        total = len(raw)

    from email_builder import build_email_html
    html = build_email_html(deals=deals, session=SESSION, total_scanned=total,
                            focus_query=FOCUS_QUERY if SESSION == "focus" else "",
                            reply_to=SMTP_USER)

    top_price = deals[0].get("price_ils", 0) if deals else 0
    top_dest  = deals[0].get("dest_name", "?") if deals else "?"
    prefix    = "[TEST] " if TEST_MODE else ""
    subject   = f"{prefix}✈️ דוח טיסות {datetime.now().strftime('%d/%m/%Y')} | הכי זול: ₪{top_price:,} ל{top_dest}"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        logger.error("All send methods failed!")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
