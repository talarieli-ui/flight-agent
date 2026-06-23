"""
main.py - Flight Scanner Agent v3 (Search Hub strategy)
Builds a curated hub of search links — no fake prices, no broken APIs.
"""
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
RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS", "tal.arieli@gmail.com,ker22ari@gmail.com").split(",")
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
        logger.info(f"Sent to {recipients}"); return True
    except Exception as e:
        logger.error(f"SMTP: {e}"); return False


def main():
    logger.info(f"Starting | session={SESSION} | focus='{FOCUS_QUERY}'")
    logger.info(f"SMTP_USER: {SMTP_USER}")

    from flight_scanner import build_search_hub
    from email_builder   import build_email_html

    hub  = build_search_hub(FOCUS_QUERY)
    html = build_email_html(hub, session=SESSION,
                            focus_query=FOCUS_QUERY,
                            reply_to=SMTP_USER)

    n_dest    = len(hub.get("destinations", []))
    n_windows = sum(len(d.get("windows", [])) for d in hub.get("destinations", []))
    now       = datetime.now()
    subject   = f"✈️ מרכז חיפוש טיסות {now.strftime('%d/%m/%Y')} | {n_dest} יעדים × {n_windows} חלונות"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
