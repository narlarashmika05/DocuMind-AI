from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time without tzinfo.

    MySQL DATETIME columns do not store a time zone, so the whole app stores UTC
    and compares naive UTC datetimes. The API adds the "Z" back when serializing.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
