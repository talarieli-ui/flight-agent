"""
main.py v5 — STRICT: only send email if real prices were verified.
If no prices found, the run FAILS visibly in GitHub Actions and NO email is sent.
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
MIN_PRICES_TO_SEND = int(os.environ.get("MIN_PRICES_TO_SEND", "1"))


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
    logger.info(f"AMADEUS_CLIENT_ID set: {bool(os.environ.get('AMADEUS_CLIENT_ID'))}")
    logger.info(f"AMADEUS_CLIENT_SECRET set: {bool(os.environ.get('AMADEUS_CLIENT_SECRET'))}")

    from flight_scanner import build_search_hub
    from email_builder   import build_email_html

    hub = build_search_hub(FOCUS_QUERY)
    n_priced = hub.get("n_priced", 0)
    n_total  = hub.get("n_total", 0)

    logger.info(f"=== RESULT: {n_priced}/{n_total} destinations with verified prices ===")

    # ── STRICT GATE: do not send email if no verified prices ────────────────
    if n_priced < MIN_PRICES_TO_SEND:
        logger.error(f"❌ FAILED: only {n_priced} priced destinations (need ≥{MIN_PRICES_TO_SEND})")
        logger.error("Email NOT sent — user requested: no prices = no email")
        logger.error("")
        logger.error("===== HOW TO FIX =====")
        logger.error("Free flight price APIs require a small one-time setup.")
        logger.error("RECOMMENDED: Amadeus Self-Service API")
        logger.error("  1. Sign up at: https://developers.amadeus.com/register")
        logger.error("  2. Create app → get Client ID + Client Secret")
        logger.error("  3. Add to GitHub Secrets:")
        logger.error("       AMADEUS_CLIENT_ID")
        logger.error("       AMADEUS_CLIENT_SECRET")
        logger.error("  4. Free: 2000 requests/month, real GDS prices")
        logger.error("======================")
        raise SystemExit(1)

    # We have real prices → build & send email
    html = build_email_html(hub, session=SESSION,
                            focus_query=FOCUS_QUERY, reply_to=SMTP_USER)

    cheapest = next((d for d in hub["destinations"] if d.get("best_price")), None)
    now      = datetime.now()
    if cheapest:
        top_price = cheapest["best_price"]["price_ils"]
        top_name  = cheapest["name"]
        subject   = f"✈️ {n_priced} מחירים מאומתים {now.strftime('%d/%m')} | הזול: ₪{top_price:,} ל{top_name}"
    else:
        subject = f"✈️ מרכז חיפוש טיסות {now.strftime('%d/%m/%Y')}"

    if not send_email(subject, html, RECIPIENT_EMAILS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
