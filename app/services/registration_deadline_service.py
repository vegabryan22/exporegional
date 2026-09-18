from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.system_setting import SystemSetting


LOCAL_TIMEZONE = ZoneInfo("America/Guatemala")
PROJECT_DEADLINE_KEY = "project_registration_closes_at"
JUDGE_DEADLINE_KEY = "judge_registration_closes_at"


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


def get_registration_deadline(key):
    return parse_local_deadline(SystemSetting.get_value(key, ""))


def registration_is_closed(key, now=None):
    deadline = get_registration_deadline(key)
    current = now or datetime.now(LOCAL_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=LOCAL_TIMEZONE)
    return bool(deadline and current >= deadline), deadline


def deadline_input_value(key):
    deadline = get_registration_deadline(key)
    return deadline.strftime("%Y-%m-%dT%H:%M") if deadline else ""


def deadline_display(deadline):
    return deadline.strftime("%d/%m/%Y a las %H:%M") if deadline else ""
