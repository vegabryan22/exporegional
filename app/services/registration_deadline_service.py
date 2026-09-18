from datetime import datetime
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo("America/Guatemala")


def parse_local_deadline(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=LOCAL_TIMEZONE)
    return parsed.astimezone(LOCAL_TIMEZONE)


def campaign_registration_deadline(campaign, registration_type):
    if not campaign:
        return None
    attribute = (
        "project_registration_closes_at"
        if registration_type == "project"
        else "judge_registration_closes_at"
    )
    return parse_local_deadline(getattr(campaign, attribute, None))


def registration_is_closed(campaign, registration_type, now=None):
    deadline = campaign_registration_deadline(campaign, registration_type)
    current = now or datetime.now(LOCAL_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=LOCAL_TIMEZONE)
    return bool(deadline and current >= deadline), deadline


def deadline_input_value(deadline):
    deadline = parse_local_deadline(deadline)
    return deadline.strftime("%Y-%m-%dT%H:%M") if deadline else ""


def deadline_display(deadline):
    return deadline.strftime("%d/%m/%Y a las %H:%M") if deadline else ""
