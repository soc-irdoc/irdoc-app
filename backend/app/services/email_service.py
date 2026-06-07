"""
Email service — console (dev) and SMTP (prod).
Falls back to console if no SMTP config is found in the database or is_enabled=False.
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_MASKED = "••••••"


async def send_email_with_config(
    to: str,
    subject: str,
    html_body: str,
    host: str,
    port: int,
    use_tls: bool,
    username: str | None,
    password: str | None,
    from_addr: str,
) -> None:
    """Low-level SMTP send using explicit credentials (used by the test endpoint)."""
    import aiosmtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    message = MIMEMultipart("alternative")
    message["From"] = from_addr
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    smtp_kwargs: dict = {
        "hostname": host,
        "port": port,
        "username": username,
        "password": password,
        "use_tls": use_tls,
    }
    smtp_kwargs = {k: v for k, v in smtp_kwargs.items() if v is not None}
    await aiosmtplib.send(message, **smtp_kwargs)
    logger.info("SMTP email sent to %s: %s", to, subject)


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    db=None,
    org_id: str | None = None,
) -> None:
    """
    Send an email.
    If db + org_id are provided, resolves SMTP config from the database.
    Falls back to console mode if no enabled config is found.
    """
    smtp_cfg = None
    if db is not None and org_id is not None:
        from app.services.smtp_config_service import get_smtp_config, get_decrypted_password
        smtp_cfg = await get_smtp_config(db, org_id)
        if smtp_cfg and not smtp_cfg.is_enabled:
            smtp_cfg = None

    if smtp_cfg is not None:
        from_name = smtp_cfg.from_name or "IRDoc"
        from_address = smtp_cfg.from_address or "noreply@localhost"
        from_addr = f"{from_name} <{from_address}>"
        await send_email_with_config(
            to=to,
            subject=subject,
            html_body=html_body,
            host=smtp_cfg.host,
            port=smtp_cfg.port,
            use_tls=smtp_cfg.use_tls,
            username=smtp_cfg.username or None,
            password=get_decrypted_password(smtp_cfg) or None,
            from_addr=from_addr,
        )
    else:
        print(
            f"\n{'='*60}\n"
            f"[EMAIL] To: {to}\n"
            f"[EMAIL] Subject: {subject}\n"
            f"[EMAIL] Body:\n{html_body}\n"
            f"{'='*60}\n"
        )
        logger.info("Console email sent to %s: %s", to, subject)


def _build_invite_html(
    inviter_name: str,
    org_name: str,
    invite_url: str,
    accent_color: str = "#6c63ff",
    logo_url: str | None = None,
    footer_text: str | None = None,
) -> str:
    logo_block = (
        f'<div style="text-align:center;margin-bottom:20px;">'
        f'<img src="{logo_url}" alt="" style="max-height:48px;"/>'
        f"</div>"
        if logo_url
        else ""
    )
    footer = footer_text or ""
    return f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  {logo_block}
  <h2 style="color: #1a1a2e;">You've been invited to IRDoc</h2>
  <p>{inviter_name} has invited you to join <strong>{org_name}</strong> on IRDoc.</p>
  <p>IRDoc is an Incident Response Documentation Platform used by SOC analysts and IR engineers.</p>
  <p style="margin: 30px 0;">
    <a href="{invite_url}"
       style="background-color: {accent_color}; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; font-weight: bold;">
      Accept Invitation
    </a>
  </p>
  <p style="color: #666; font-size: 14px;">This link expires in 48 hours.</p>
  <p style="color: #666; font-size: 12px;">
    If you did not expect this invitation, you can safely ignore this email.
  </p>
  {f'<p style="color: #999; font-size: 11px; margin-top: 30px;">{footer}</p>' if footer else ""}
</body>
</html>"""


async def send_invite_email(
    to: str,
    inviter_name: str,
    org_name: str,
    token: str,
    db=None,
    org_id: str | None = None,
) -> None:
    """Send an invitation email. Uses DB SMTP config when db + org_id are provided."""
    invite_url = f"{str(settings.BASE_URL).rstrip('/')}/invite/{token}"

    smtp_cfg = None
    if db is not None and org_id is not None:
        from app.services.smtp_config_service import get_smtp_config
        smtp_cfg = await get_smtp_config(db, org_id)
        if smtp_cfg and not smtp_cfg.is_enabled:
            smtp_cfg = None

    accent_color = smtp_cfg.accent_color if smtp_cfg else "#6c63ff"
    logo_url = smtp_cfg.logo_url if smtp_cfg else None
    footer_text = smtp_cfg.footer_text if smtp_cfg else None
    subject_template = smtp_cfg.subject_template if smtp_cfg else "You've been invited to join {org_name}"
    subject = subject_template.format(org_name=org_name)

    html_body = _build_invite_html(
        inviter_name=inviter_name,
        org_name=org_name,
        invite_url=invite_url,
        accent_color=accent_color,
        logo_url=logo_url,
        footer_text=footer_text,
    )
    await send_email(to, subject, html_body, db=db, org_id=org_id)
