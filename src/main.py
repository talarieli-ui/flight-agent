"""main.py v7 — STRICT: no email if no verified OTA prices."""
import os, smtplib, logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SMTP_HOST        = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER        = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS",
    "tal.arieli@gmail.com,ker22ari@gmail.com").split(",")
SESSION          = os.environ.get("EMAIL_SESSION", "morning")
FOCUS_QUERY      = os.environ.get("FOCUS_QUERY", "").strip()


def send_email(subject, html_body, recipients):
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
        logger.info(f"Sent to {recipients}")
        return True
    except Exception as e:
        logger.error(f"SMTP: {e}")
        return False


def main():
    logger.info(f"Starting | session={SESSION} | focus='{FOCUS_QUERY}'")

    from flight_scanner import build_search_hub
    from email_builder   import build_email_html

    hub = build_search_hub(FOCUS_QUERY)
    n_priced = hub.get("n_priced", 0)
    n_total  = hub.get("n_total", 0)
    calls    = hub.get("calls_made", 0)
    quota    = hub.get("quota_left", 0)

    logger.info(f"=== Result: {n_priced}/{n_total} priced | {calls} API calls | quota left: {quota} ===")

    if n_priced < 1:
        logger.error("❌ NO verified OTA prices found — NOT sending email")
        raise SystemExit(1)

    html = build_email_html(hub, session=SESSION,
                            focus_query=FOCUS_QUERY, reply_to=SMTP_USER)

    cheapest = next((d for d in hub["destinations"] if d.get("best_price_ils")), None)
    now = datetime.now()
    if cheapest:
        top_price = cheapest["best_price_ils"]
        top_name  = cheapest["name"]
        subject   = f"✈️ {n_priced} מחירים מאומתים {now.strftime('%d/%m')} | מ-₪{top_price:,} ל{top_name}"
    else:
        subject = f"✈️ מחירי טיסה {now.strftime('%d/%m/%Y')}"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
