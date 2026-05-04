from datetime import datetime
import pytz
import re


class ReqsHandler:

    FORMAT = "%Y-%m-%d %H:%M:%S"
    TIMEZONE = pytz.timezone("Asia/Kolkata")

    def __init__(self, interval_minutes: int):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60

    # -----------------------------
    def normalize(self, start_str: str, end_str: str):

        start = self._parse_datetime(start_str)
        end   = self._parse_datetime(end_str)

        now = self._now()

        if end > now:
            end = now

        start = self._floor_to_interval(start)
        end   = self._floor_to_interval(end)

        if start >= end:
            raise ValueError("Invalid time range")

        return int(start.timestamp()), int(end.timestamp())

    # -----------------------------
    def _parse_datetime(self, dt_str: str):

        if not self._validate_format(dt_str):
            raise ValueError("Invalid format")

        dt = datetime.strptime(dt_str, self.FORMAT)
        dt = self.TIMEZONE.localize(dt)

        return dt

    # -----------------------------
    def _validate_format(self, dt_str: str):
        pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
        return re.match(pattern, dt_str) is not None

    # -----------------------------
    def _now(self):
        return datetime.now(self.TIMEZONE)

    # -----------------------------
    def _floor_to_interval(self, dt: datetime):
        epoch = int(dt.timestamp())
        floored = epoch - (epoch % self.interval_seconds)
        return datetime.fromtimestamp(floored, tz=self.TIMEZONE)


# -----------------------------
# TEST
handler = ReqsHandler(interval_minutes=5)

ex_start = "2026-05-04 01:00:30"
ex_end   = "2026-05-04 01:45:00"

print(handler._parse_datetime(ex_start))
print(handler._parse_datetime(ex_end))
print(handler.normalize(ex_start, ex_end))