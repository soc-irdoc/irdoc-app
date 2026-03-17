"""
Email service — console (dev) and SMTP (prod).
EMAIL_BACKEND=console prints to stdout.
EMAIL_BACKEND=smtp sends via aiosmtplib.
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an email using the configured backend."""
    if settings.EMAIL_BACKEND == "console":
        print(
            f"\n{'='*60}\n"
            f"[EMAIL] To: {to}\n"
            f"[EMAIL] Subject: {subject}\n"
            f"[EMAIL] Body:\n{html_body}\n"
            f"{'='*60}\n"
        )
        logger.info("Console email sent to %s: %s", to, subject)
    elif settings.EMAIL_BACKEND == "smtp":
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        message = MIMEMultipart("alternative")
        message["From"] = settings.EMAIL_FROM
        message["To"] = to
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        smtp_kwargs: dict = {
            "hostname": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "username": settings.SMTP_USER or None,
            "password": settings.SMTP_PASSWORD or None,
            "use_tls": settings.SMTP_TLS,
        }
        # Remove None values to avoid aiosmtplib complaints
        smtp_kwargs = {k: v for k, v in smtp_kwargs.items() if v is not None}

        await aiosmtplib.send(message, **smtp_kwargs)
        logger.info("SMTP email sent to %s: %s", to, subject)
    else:
        logger.warning(
            "Unknown EMAIL_BACKEND '%s' — email to %s not sent",
            settings.EMAIL_BACKEND,
            to,
        )


async def send_invite_email(
    to: str, inviter_name: str, org_name: str, token: str
) -> None:
    """Send an invitation email with an accept link."""
    invite_url = f"{str(settings.BASE_URL).rstrip('/')}/invite/{token}"
    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a2e;">You've been invited to IRDoc</h2>
  <p>{inviter_name} has invited you to join <strong>{org_name}</strong> on IRDoc.</p>
  <p>IRDoc is an Incident Response Documentation Platform used by SOC analysts and IR engineers.</p>
  <p style="margin: 30px 0;">
    <a href="{invite_url}"
       style="background-color: #6c63ff; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; font-weight: bold;">
      Accept Invitation
    </a>
  </p>
  <p style="color: #666; font-size: 14px;">This link expires in 48 hours.</p>
  <p style="color: #666; font-size: 12px;">
    If you did not expect this invitation, you can safely ignore this email.
  </p>
</body>
</html>"""
    await send_email(to, f"Invitation to join {org_name} on IRDoc", html_body)
