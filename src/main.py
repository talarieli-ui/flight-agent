"""
main.py – נקודת כניסה ראשית לסוכן הטיסות
תומך במצבים:
  - daily scan (morning/evening) — EMAIL_SESSION=morning|evening
  - focused scan — EMAIL_SESSION=focus, FOCUS_QUERY=<destination>
"""

import os
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flight_scanner import scan_all_flights, scan_focused, find_best_deals
from email_builder import build_email_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

SMTP_HOST        = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER        = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAILS = os.environ.get(
    "RECIPIENT_EMAILS", "tal.arieli@gmail.com,ker22ari@gmail.com"
).split(",")
SESSION     = os.environ.get("EMAIL_SESSION", "morning")   # morning | evening | focus
FOCUS_QUERY = os.environ.get("FOCUS_QUERY", "").strip()    # e.g. "לונדון" or "LHR"


def send_email(subject: str, html_body: str, recipients: list[str]) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("❌ SMTP_USER / SMTP_PASSWORD not set.")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"✈️ Flight Scanner <{SMTP_USER}>"
    msg["To"]      = ", ".join(recipients)
    msg["Reply-To"] = SMTP_USER   # replies trigger focused scan
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
            srv.ehlo(); srv.starttls()
            srv.login(SMTP_USER, SMTP_PASSWORD)
            srv.sendmail(SMTP_USER, recipients, msg.as_bytes())
        logger.info(f"✅ Email sent to {', '.join(recipients)}")
        return True
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False


def main():
    now = datetime.now()
    logger.info(f"🚀 Flight Scanner starting | session={SESSION} | focus='{FOCUS_QUERY}'")

    is_focused = SESSION == "focus" and FOCUS_QUERY

    if is_focused:
        raw = scan_focused(FOCUS_QUERY)
    else:
        raw = scan_all_flights()

    best = find_best_deals(raw, top_n=20)
    logger.info(f"📊 Best deals: {len(best)}")

    html = build_email_html(
        deals=best,
        session=SESSION,
        total_scanned=len(raw),
        focus_query=FOCUS_QUERY if is_focused else "",
        reply_to=SMTP_USER,
    )

    # Subject
    top_price = best[0].get("price_ils", 0) if best else 0
    top_dest  = best[0].get("dest_name", "?") if best else "?"
    if is_focused:
        subject = f"🔍 דוח ממוקד – {FOCUS_QUERY} | מחיר מינימום: ₪{top_price:,}"
    else:
        emoji = "🌅" if SESSION == "morning" else "🌙"
        subject = (
            f"{emoji} דוח טיסות {now.strftime('%d/%m/%Y')} | "
            f"הכי זול: ₪{top_price:,} ל{top_dest}"
        )

    ok = send_email(subject, html, RECIPIENT_EMAILS)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
