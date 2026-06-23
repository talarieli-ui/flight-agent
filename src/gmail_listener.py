"""
gmail_listener.py – מאזין לתיבת Gmail לחיפוש מיילים עם subject 'FOCUS: <destination>'
מופעל כ-GitHub Action נפרד שרץ כל 10 דקות.
"""

import os
import imaplib
import email
import subprocess
import logging
from email.header import decode_header

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

IMAP_HOST     = os.environ.get("IMAP_HOST", "imap.gmail.com")
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALLOWED_SENDERS = os.environ.get(
    "ALLOWED_FOCUS_SENDERS",
    "tal.arieli@gmail.com,ker22ari@gmail.com"
).split(",")


def decode_str(s):
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="replace")
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result


def check_focus_emails() -> list[str]:
    """Return list of focus queries found in unread FOCUS: emails."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("No SMTP credentials configured.")
        return []

    queries = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select("INBOX")

        _, data = mail.search(None, '(UNSEEN SUBJECT "FOCUS:")')
        ids = data[0].split()
        logger.info(f"Found {len(ids)} unread FOCUS emails.")

        for eid in ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            sender = decode_str(msg.get("From", ""))
            subject = decode_str(msg.get("Subject", ""))

            # Security: only process emails from allowed senders
            allowed = any(a.lower() in sender.lower() for a in ALLOWED_SENDERS)
            if not allowed:
                logger.warning(f"Ignoring FOCUS email from unknown sender: {sender}")
                continue

            # Extract query from subject: 'FOCUS: <query>'
            if "FOCUS:" in subject.upper():
                query = subject.upper().split("FOCUS:", 1)[1].strip()
                if query:
                    queries.append(query)
                    logger.info(f"FOCUS request from {sender}: '{query}'")

            # Mark as read
            mail.store(eid, "+FLAGS", "\\Seen")

        mail.logout()
    except Exception as e:
        logger.error(f"IMAP error: {e}")

    return queries


def trigger_focused_scan(query: str):
    """Run main.py with FOCUS mode for the given query."""
    env = os.environ.copy()
    env["EMAIL_SESSION"] = "focus"
    env["FOCUS_QUERY"]   = query
    logger.info(f"🔍 Triggering focused scan for: '{query}'")
    result = subprocess.run(
        ["python", "main.py"],
        env=env, capture_output=True, text=True
    )
    if result.returncode == 0:
        logger.info(f"✅ Focused scan sent for '{query}'")
    else:
        logger.error(f"❌ Focused scan failed:\n{result.stderr}")


def main():
    queries = check_focus_emails()
    for q in queries:
        trigger_focused_scan(q)
    if not queries:
        logger.info("No FOCUS emails found — nothing to do.")


if __name__ == "__main__":
    main()
