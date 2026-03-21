from datetime import datetime

import pytz

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def pretty_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is not None:
            dt = dt.astimezone(VIETNAM_TZ)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return ts
