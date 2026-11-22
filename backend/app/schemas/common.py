import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, StringConstraints


def _as_utc(value: datetime) -> datetime:
    # The database returns naive UTC datetimes; mark them as UTC so JSON gets a "Z" suffix
    # and the browser converts them to the user's local time correctly.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _check_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]

# max_length stops attackers from sending megabyte-long passwords to the (slow) hasher
Password = Annotated[str, StringConstraints(min_length=8, max_length=128), AfterValidator(_check_password_strength)]

FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]

Language = Literal["en", "te"]
