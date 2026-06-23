"""
main.py - Flight Scanner Agent entry point
TEST_MODE: uses mock data focused on Greek islands + Prague July-Aug.
Max price: ₪1,200
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


def _d(base_date, hour=7, minute=0):
    return base_date.replace(hour=hour, minute=minute, second=0).strftime("%Y-%m-%dT%H:%M:00")


def build_mock_deals():
    now = datetime.now()
    jul1 = datetime(2026, 7, 1)
    aug1 = datetime(2026, 8, 1)

    return [
        # ── איי יוון ──────────────────────────────────────────────────────
        {
            "destination": "KGS", "dest_name": "קוס",
            "price_ils": 620,
            "departure": _d(jul1 + timedelta(days=10), 6, 30),
            "arrival":   _d(jul1 + timedelta(days=10), 8, 0),
            "return_departure": _d(jul1 + timedelta(days=17), 15, 0),
            "return_arrival":   _d(jul1 + timedelta(days=17), 16, 30),
            "stops": 0, "airline": "Ryanair", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "10 יולי",
        },
        {
            "destination": "RHO", "dest_name": "רודוס",
            "price_ils": 690,
            "departure": _d(jul1 + timedelta(days=5), 7, 0),
            "arrival":   _d(jul1 + timedelta(days=5), 8, 30),
            "return_departure": _d(jul1 + timedelta(days=12), 14, 0),
            "return_arrival":   _d(jul1 + timedelta(days=12), 15, 35),
            "stops": 0, "airline": "Arkia", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "5 יולי",
        },
        {
            "destination": "CFU", "dest_name": "קורפו",
            "price_ils": 750,
            "departure": _d(jul1 + timedelta(days=14), 6, 45),
            "arrival":   _d(jul1 + timedelta(days=14), 8, 15),
            "return_departure": _d(jul1 + timedelta(days=21), 16, 0),
            "return_arrival":   _d(jul1 + timedelta(days=21), 17, 30),
            "stops": 0, "airline": "Wizz Air", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "14 יולי",
        },
        {
            "destination": "EFL", "dest_name": "קפלוניה",
            "price_ils": 810,
            "departure": _d(jul1 + timedelta(days=20), 7, 30),
            "arrival":   _d(jul1 + timedelta(days=20), 9, 10),
            "return_departure": _d(jul1 + timedelta(days=27), 15, 30),
            "return_arrival":   _d(jul1 + timedelta(days=27), 17, 15),
            "stops": 0, "airline": "Ryanair", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "20 יולי",
        },
        {
            "destination": "PVK", "dest_name": "לפקדה / פרבזה",
            "price_ils": 870,
            "departure": _d(aug1 + timedelta(days=3), 6, 0),
            "arrival":   _d(aug1 + timedelta(days=3), 7, 45),
            "return_departure": _d(aug1 + timedelta(days=10), 14, 0),
            "return_arrival":   _d(aug1 + timedelta(days=10), 15, 50),
            "stops": 0, "airline": "Wizz Air", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "3 אוגוסט",
        },
        {
            "destination": "ZTH", "dest_name": "זקינתוס",
            "price_ils": 890,
            "departure": _d(aug1 + timedelta(days=7), 7, 15),
            "arrival":   _d(aug1 + timedelta(days=7), 9, 0),
            "return_departure": _d(aug1 + timedelta(days=14), 13, 0),
            "return_arrival":   _d(aug1 + timedelta(days=14), 14, 50),
            "stops": 0, "airline": "Arkia", "source": "Aviasales",
            "deep_link": "", "origin": "TLV", "window_label": "7 אוגוסט",
        },
        {
            "destination": "SKG", "dest_name": "חלקידיקי / סלוניקי",
            "price_ils": 940,
            "departure": _d(jul1 + timedelta(days=8), 6, 55),
            "arrival":   _d(jul1 + timedelta(days=8), 8, 30),
            "return_departure": _d(jul1 + timedelta(days=15), 15, 30),
            "return_arrival":   _d(jul1 + timedelta(days=15), 17, 10),
            "stops": 0, "airline": "EL AL", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "8 יולי",
        },
        {
            "destination": "JTR", "dest_name": "סנטוריני",
            "price_ils": 980,
            "departure": _d(aug1 + timedelta(days=12), 8, 0),
            "arrival":   _d(aug1 + timedelta(days=12), 9, 55),
            "return_departure": _d(aug1 + timedelta(days=19), 16, 0),
            "return_arrival":   _d(aug1 + timedelta(days=19), 18, 0),
            "stops": 0, "airline": "Ryanair", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "12 אוגוסט",
        },
        {
            "destination": "JMK", "dest_name": "מיקונוס",
            "price_ils": 1050,
            "departure": _d(aug1 + timedelta(days=5), 7, 30),
            "arrival":   _d(aug1 + timedelta(days=5), 9, 20),
            "return_departure": _d(aug1 + timedelta(days=12), 15, 0),
            "return_arrival":   _d(aug1 + timedelta(days=12), 17, 0),
            "stops": 0, "airline": "Arkia", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "5 אוגוסט",
        },
        {
            "destination": "HER", "dest_name": "כרתים (הרקליון)",
            "price_ils": 1080,
            "departure": _d(jul1 + timedelta(days=25), 6, 30),
            "arrival":   _d(jul1 + timedelta(days=25), 8, 20),
            "return_departure": _d(aug1 + timedelta(days=1), 14, 0),
            "return_arrival":   _d(aug1 + timedelta(days=1), 15, 55),
            "stops": 0, "airline": "EL AL", "source": "Google Flights",
            "deep_link": "", "origin": "TLV", "window_label": "25 יולי",
        },
        {
            "destination": "ATH", "dest_name": "אתונה",
            "price_ils": 1150,
            "departure": _d(jul1 + timedelta(days=3), 6, 45),
            "arrival":   _d(jul1 + timedelta(days=3), 8, 45),
            "return_departure": _d(jul1 + timedelta(days=10), 14, 0),
            "return_arrival":   _d(jul1 + timedelta(days=10), 16, 5),
            "stops": 0, "airline": "Aegean", "source": "Aviasales",
            "deep_link": "", "origin": "TLV", "window_label": "3 יולי",
        },
        # ── פראג — יולי-אוגוסט בלבד ──────────────────────────────────────
        {
            "destination": "PRG", "dest_name": "פראג",
            "price_ils": 990,
            "departure": _d(jul1 + timedelta(days=12), 8, 30),
            "arrival":   _d(jul1 + timedelta(days=12), 10, 50),
            "return_departure": _d(jul1 + timedelta(days=19), 15, 0),
            "return_arrival":   _d(jul1 + timedelta(days=19), 17, 25),
            "stops": 0, "airline": "Wizz Air", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "12 יולי",
        },
        {
            "destination": "PRG", "dest_name": "פראג",
            "price_ils": 1100,
            "departure": _d(aug1 + timedelta(days=8), 9, 0),
            "arrival":   _d(aug1 + timedelta(days=8), 11, 20),
            "return_departure": _d(aug1 + timedelta(days=15), 16, 0),
            "return_arrival":   _d(aug1 + timedelta(days=15), 18, 25),
            "stops": 0, "airline": "Wizz Air", "source": "Kiwi.com",
            "deep_link": "", "origin": "TLV", "window_label": "8 אוגוסט",
        },
        # טיסה מעל ₪1,200 — לא אמורה להופיע
        {
            "destination": "BCN", "dest_name": "ברצלונה",
            "price_ils": 1490,
            "departure": _d(jul1 + timedelta(days=20), 8, 0),
            "arrival":   _d(jul1 + timedelta(days=20), 12, 5),
            "return_departure": "", "return_arrival": "",
            "stops": 0, "airline": "Vueling", "source": "Aviasales",
            "deep_link": "", "origin": "TLV", "window_label": "20 יולי",
        },
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
    logger.info(f"SMTP_USER: {'set' if SMTP_USER else 'MISSING'} | password: {len(SMTP_PASSWORD)} chars")
    logger.info(f"Recipients: {RECIPIENT_EMAILS}")

    if TEST_MODE:
        logger.info("TEST MODE: mock data (Greek islands + Prague July-Aug, max ₪1,200)")
        all_deals = build_mock_deals()
        # Apply price filter — same as real scanner
        deals = [d for d in all_deals if d.get("price_ils", 99999) <= 1200]
        logger.info(f"After ₪1,200 filter: {len(deals)}/{len(all_deals)} deals")
        total = len(deals)
    else:
        from flight_scanner import scan_all_flights, scan_focused, find_best_deals
        raw   = scan_focused(FOCUS_QUERY) if SESSION == "focus" and FOCUS_QUERY else scan_all_flights()
        deals = find_best_deals(raw, top_n=20)
        total = len(raw)

    from email_builder import build_email_html
    html = build_email_html(
        deals=deals,
        session=SESSION,
        total_scanned=total,
        focus_query=FOCUS_QUERY if SESSION == "focus" else "",
        reply_to=SMTP_USER,
    )

    top_price = deals[0].get("price_ils", 0) if deals else 0
    top_dest  = deals[0].get("dest_name", "?") if deals else "?"
    prefix    = "[TEST] " if TEST_MODE else ""
    subject   = f"{prefix}✈️ טיסות ישירות {datetime.now().strftime('%d/%m/%Y')} | הזול ביותר: ₪{top_price:,} ל{top_dest}"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
