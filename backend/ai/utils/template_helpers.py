# ai/utils/template_helpers.py
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "America/Denver"


def get_current_day(timezone: str = DEFAULT_TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone)).strftime("%A")
