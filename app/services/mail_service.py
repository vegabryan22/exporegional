import smtplib
from email.message import EmailMessage

from app.models.system_setting import SystemSetting


def _log_email(to_email: str, subject: str, ok: bool, error: str | None):
    try:
        from app.services.audit_service import log_event
        from app.extensions import db
        status = "enviado" if ok else f"error: {error}"
        log_event(
            "system.email.send",
            "email",
            detail=f"Para: {to_email} | Asunto: {subject} | Estado: {status}",
        )
        db.session.commit()
    except Exception:  # noqa: BLE001
        pass


def get_smtp_config():
    return {
        "host": SystemSetting.get_value("smtp_host", ""),
        "port": int(SystemSetting.get_value("smtp_port", "587") or 587),
        "username": SystemSetting.get_value("smtp_username", ""),
        "password": SystemSetting.get_value("smtp_password", ""),
        "from_email": SystemSetting.get_value("smtp_from_email", ""),
        "use_tls": SystemSetting.get_value("smtp_use_tls", "1") == "1",
        "use_ssl": SystemSetting.get_value("smtp_use_ssl", "0") == "1",
    }


def smtp_is_configured():
    config = get_smtp_config()
    return bool(config["host"] and config["port"] and config["from_email"])


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None):
    config = get_smtp_config()
    if not smtp_is_configured():
        return False, "SMTP no configurado."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_email"]
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if config["use_ssl"]:
            server = smtplib.SMTP_SSL(config["host"], config["port"], timeout=15)
        else:
            server = smtplib.SMTP(config["host"], config["port"], timeout=15)

        with server:
            if config["use_tls"] and not config["use_ssl"]:
                server.starttls()
            if config["username"]:
                server.login(config["username"], config["password"])
            server.send_message(message)
    except Exception as error:  # noqa: BLE001
        _log_email(to_email, subject, ok=False, error=str(error))
        return False, str(error)

    _log_email(to_email, subject, ok=True, error=None)
    return True, None
