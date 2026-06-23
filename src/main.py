"""
main.py - Flight Scanner Agent
Real prices only — no mock data, no estimated prices.
If no verified prices found, email says so.
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


def send_via_sendgrid(subject, html_body, recipients):
    payload = json.dumps({
        "personalizations": [{"to": [{"email": r} for r in recipients]}],
        "from": {"email": SMTP_USER, "name": "Flight Scanner"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}]
    }).encode()
    req = urllib.request.Request("https://api.sendgrid.com/v3/mail/send", data=payload,
        headers={"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"},
        method="POST")
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
    logger.info(f"Starting | session={SESSION} | focus='{FOCUS_QUERY}'")
    logger.info(f"SMTP_USER: {'set' if SMTP_USER else 'MISSING'} | {len(SMTP_PASSWORD)} chars")
    logger.info(f"SERPAPI_KEY: {'set' if os.environ.get('SERPAPI_KEY') else 'not set'}")
    logger.info(f"AVIASALES_TOKEN: {'set' if os.environ.get('AVIASALES_TOKEN') else 'not set (using public)'}")

    # Real scan only
    from flight_scanner import scan_all_flights, scan_focused, find_best_deals
    raw   = scan_focused(FOCUS_QUERY) if SESSION == "focus" and FOCUS_QUERY else scan_all_flights()
    deals = find_best_deals(raw, top_n=20)
    total = len(raw)

    logger.info(f"Verified deals under ₪1,200: {len(deals)}")

    from email_builder import build_email_html
    html = build_email_html(
        deals=deals,
        session=SESSION,
        total_scanned=total,
        focus_query=FOCUS_QUERY if SESSION == "focus" else "",
        reply_to=SMTP_USER,
    )

    now = datetime.now()
    if deals:
        top_price = deals[0]["price_ils"]
        top_dest  = deals[0]["dest_name"]
        subject = f"✈️ טיסות ישירות {now.strftime('%d/%m/%Y')} | הזול ביותר: ₪{top_price:,} ל{top_dest}"
    else:
        subject = f"✈️ דוח טיסות {now.strftime('%d/%m/%Y')} | לא נמצאו עסקאות מתחת ל-₪1,200"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
