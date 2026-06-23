"""
main.py - Flight Scanner Agent entry point
TEST_MODE: uses mock data (no real API calls).
"""
import os, smtplib, logging, urllib.request, json
from datetime import datetime, timedelta
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
TEST_MODE        = os.environ.get("TEST_MODE", "false").lower() == "true"
SENDGRID_KEY     = os.environ.get("SENDGRID_API_KEY", "")


def _d(days_ahead, hour=6, minute=0):
    """Return ISO datetime string N days from now."""
    dt = datetime.now() + timedelta(days=days_ahead)
    return dt.replace(hour=hour, minute=minute, second=0).strftime("%Y-%m-%dT%H:%M:00")


MOCK_DEALS = [
    {"destination":"BUD","dest_name":"\u05d1\u05d5\u05d3\u05e4\u05e9\u05d8", "price_ils":890,  "departure":_d(5,7,0),  "arrival":_d(5,9,15),  "return_departure":_d(12,16,0), "return_arrival":_d(12,18,20), "stops":0,"airline":"Wizz Air",   "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"5 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"PRG","dest_name":"\u05e4\u05e8\u05d0\u05d2",              "price_ils":950,  "departure":_d(4,8,30), "arrival":_d(4,10,50), "return_departure":_d(11,15,0), "return_arrival":_d(11,17,25), "stops":0,"airline":"Wizz Air",   "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"4 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"ATH","dest_name":"\u05d0\u05ea\u05d5\u05e0\u05d4",        "price_ils":1050, "departure":_d(6,6,45), "arrival":_d(6,8,45),  "return_departure":_d(13,14,0), "return_arrival":_d(13,16,5),  "stops":0,"airline":"Aegean",     "source":"Aviasales",   "deep_link":"","origin":"TLV","window_label":"6 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"VIE","dest_name":"\u05d5\u05d9\u05e0\u05d4",              "price_ils":1120, "departure":_d(7,7,20), "arrival":_d(7,9,55),  "return_departure":_d(14,18,0), "return_arrival":_d(14,20,40), "stops":0,"airline":"Austrian",   "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"7 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"LHR","dest_name":"\u05dc\u05d5\u05e0\u05d3\u05d5\u05df",  "price_ils":1290, "departure":_d(10,6,0), "arrival":_d(10,10,20),"return_departure":_d(17,12,0), "return_arrival":_d(17,17,15), "stops":0,"airline":"EL AL",      "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"10 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"BCN","dest_name":"\u05d1\u05e8\u05e6\u05dc\u05d5\u05e0\u05d4","price_ils":1490,"departure":_d(14,8,0),"arrival":_d(14,12,5),"return_departure":_d(21,17,0),"return_arrival":_d(21,21,0),  "stops":0,"airline":"Vueling",    "source":"Aviasales",   "deep_link":"","origin":"TLV","window_label":"14 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"CDG","dest_name":"\u05e4\u05e8\u05d9\u05d6",              "price_ils":1550, "departure":_d(21,7,30),"arrival":_d(21,11,45),"return_departure":_d(28,16,0),"return_arrival":_d(28,20,20),  "stops":0,"airline":"Air France", "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"21 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"DXB","dest_name":"\u05d3\u05d5\u05d1\u05d0\u05d9",        "price_ils":1380, "departure":_d(8,1,55), "arrival":_d(8,5,0),   "return_departure":_d(15,8,0),  "return_arrival":_d(15,11,10), "stops":0,"airline":"Emirates",   "source":"Google Flights","deep_link":"","origin":"TLV","window_label":"8 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"MAD","dest_name":"\u05de\u05d3\u05e8\u05d9\u05d3",        "price_ils":1650, "departure":_d(28,7,0), "arrival":_d(28,11,20),"return_departure":_d(35,14,0), "return_arrival":_d(35,18,25), "stops":0,"airline":"Iberia",     "source":"Aviasales",   "deep_link":"","origin":"TLV","window_label":"28 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"BKK","dest_name":"\u05d1\u05e0\u05d2\u05e7\u05d5\u05e7",  "price_ils":2490, "departure":_d(60,0,30),"arrival":_d(60,9,30), "return_departure":_d(74,23,0), "return_arrival":_d(75,5,30),  "stops":0,"airline":"Thai",       "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"60 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"JFK","dest_name":"\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7","price_ils":3200,"departure":_d(45,22,0),"arrival":_d(46,4,0),"return_departure":_d(52,23,30),"return_arrival":_d(53,16,0),"stops":0,"airline":"Delta",     "source":"Google Flights","deep_link":"","origin":"TLV","window_label":"45 \u05d9\u05de\u05d9\u05dd"},
    {"destination":"LIS","dest_name":"\u05dc\u05d9\u05e1\u05d1\u05d5\u05df",  "price_ils":1720, "departure":_d(35,6,0), "arrival":_d(35,11,0), "return_departure":_d(42,15,0), "return_arrival":_d(42,20,5),  "stops":0,"airline":"TAP",        "source":"Kiwi.com",    "deep_link":"","origin":"TLV","window_label":"35 \u05d9\u05de\u05d9\u05dd"},
]


def send_via_sendgrid(subject, html_body, recipients):
    payload = json.dumps({
        "personalizations": [{"to": [{"email": r} for r in recipients]}],
        "from": {"email": SMTP_USER, "name": "Flight Scanner"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}]
    }).encode()
    req = urllib.request.Request("https://api.sendgrid.com/v3/mail/send", data=payload,
        headers={"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status in (200, 202)
    except Exception as e:
        logger.error(f"SendGrid: {e}"); return False


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
        logger.info(f"SMTP sent to {recipients}"); return True
    except Exception as e:
        logger.error(f"SMTP: {e}"); return False


def send_email(subject, html_body, recipients):
    if SENDGRID_KEY:
        if send_via_sendgrid(subject, html_body, recipients): return True
    return send_via_smtp(subject, html_body, recipients)


def main():
    logger.info(f"Starting | session={SESSION} | test={TEST_MODE}")
    logger.info(f"SMTP_USER: {'set' if SMTP_USER else 'MISSING'}")
    logger.info(f"SMTP_PASSWORD: {len(SMTP_PASSWORD)} chars")
    logger.info(f"Recipients: {RECIPIENT_EMAILS}")

    if TEST_MODE:
        logger.info("TEST MODE: mock data")
        deals = MOCK_DEALS
        total = len(deals)
    else:
        from flight_scanner import scan_all_flights, scan_focused, find_best_deals
        raw   = scan_focused(FOCUS_QUERY) if SESSION == "focus" and FOCUS_QUERY else scan_all_flights()
        deals = find_best_deals(raw, top_n=20)
        total = len(raw)

    from email_builder import build_email_html
    html = build_email_html(deals=deals, session=SESSION, total_scanned=total,
                            focus_query=FOCUS_QUERY if SESSION=="focus" else "",
                            reply_to=SMTP_USER)

    top_price = deals[0].get("price_ils", 0) if deals else 0
    top_dest  = deals[0].get("dest_name", "?") if deals else "?"
    prefix    = "[TEST] " if TEST_MODE else ""
    subject   = f"{prefix}✈️ טיסות ישירות {datetime.now().strftime('%d/%m/%Y')} | הזול ביותר: ₪{top_price:,} ל{top_dest}"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
