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
        "provider": SystemSetting.get_value("smtp_provider", "custom"),
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
    base_ready = bool(config["host"] and config["port"] and config["from_email"])
    if config["provider"] == "gmail" or config["host"].strip().lower() == "smtp.gmail.com":
        return base_ready and bool(config["username"] and config["password"])
    return base_ready


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
        error_text = str(error)
        if config["provider"] == "gmail" and ("535" in error_text or "Username and Password not accepted" in error_text):
            error_text = (
                "Gmail rechazó las credenciales. Use el correo completo y una contraseña "
                "de aplicación de Google, no la contraseña habitual de la cuenta."
            )
        _log_email(to_email, subject, ok=False, error=error_text)
        return False, error_text

    _log_email(to_email, subject, ok=True, error=None)
    return True, None


def send_email_batch(messages: list[dict]):
    """Send multiple personalized messages over one SMTP connection."""
    config = get_smtp_config()
    if not smtp_is_configured():
        return [(False, "SMTP no configurado.") for _ in messages]

    prepared = []
    for item in messages:
        message = EmailMessage()
        message["Subject"] = item["subject"]
        message["From"] = config["from_email"]
        message["To"] = item["to_email"]
        message.set_content(item["body"])
        if item.get("html_body"):
            message.add_alternative(item["html_body"], subtype="html")
        prepared.append((item, message))

    try:
        if config["use_ssl"]:
            server = smtplib.SMTP_SSL(config["host"], config["port"], timeout=30)
        else:
            server = smtplib.SMTP(config["host"], config["port"], timeout=30)
        with server:
            if config["use_tls"] and not config["use_ssl"]:
                server.starttls()
            if config["username"]:
                server.login(config["username"], config["password"])
            results = []
            for item, message in prepared:
                try:
                    server.send_message(message)
                    results.append((True, None))
                    _log_email(item["to_email"], item["subject"], ok=True, error=None)
                except Exception as error:  # noqa: BLE001
                    error_text = str(error)
                    results.append((False, error_text))
                    _log_email(item["to_email"], item["subject"], ok=False, error=error_text)
            return results
    except Exception as error:  # noqa: BLE001
        error_text = str(error)
        for item in messages:
            _log_email(item["to_email"], item["subject"], ok=False, error=error_text)
        return [(False, error_text) for _ in messages]
