from datetime import datetime, timedelta


def format_recent_datetime(dt: datetime, now: datetime | None = None) -> str:
    if not isinstance(dt, datetime):
        return ""
    current = now or datetime.now()
    try:
        delta = current - dt
        if delta < timedelta(hours=24):
            return dt.strftime("%H:%M:%S")
        if delta < timedelta(days=7):
            return dt.strftime("%A")
        if delta < timedelta(days=30):
            return dt.strftime("%-d %B")
        return dt.strftime("%-d %b, %Y")
    except Exception:
        return ""


def format_recent_timestamp(timestamp: float) -> str:
    if not timestamp:
        return ""
    try:
        return format_recent_datetime(datetime.fromtimestamp(timestamp))
    except Exception:
        return ""


def format_recent_datetime_string(value: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if not value:
        return ""
    try:
        return format_recent_datetime(datetime.strptime(str(value), fmt))
    except Exception:
        return str(value)
