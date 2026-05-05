from datetime import datetime
import pytz

from config import (
    DATETIME_FORMAT,
    TIMEZONE,
    INTERVAL_MAP,
    DEFAULT_INTERVAL,
    AVAILABILITY_LIMITS,
    FETCH_LIMITS
)


class ReqsHandler:
    """
    Handles:
    - datetime parsing
    - normalization
    - interval alignment
    - timestamp conversion
    - availability validation
    - chunk decision
    """

    def __init__(self, interval=None, timezone=None, dt_format=None):

        self.interval = interval or DEFAULT_INTERVAL

        if self.interval not in INTERVAL_MAP:
            raise ValueError(f"Invalid interval: {self.interval}")

        self.interval_seconds = INTERVAL_MAP[self.interval]

        self.format = dt_format or DATETIME_FORMAT
        self.timezone = pytz.timezone(timezone or TIMEZONE)

    # --------------------------------------------------
    # MAIN NORMALIZATION
    # --------------------------------------------------
    def normalize(self, start_str: str, end_str: str):
        """
        Converts input → normalized timestamps
        """

        start = self._parse_datetime(start_str)
        end   = self._parse_datetime(end_str)

        now = self._now()

        # clamp future
        if end > now:
            end = now

        # align to interval
        start = self._floor_to_interval(start)
        end   = self._floor_to_interval(end)

        if start >= end:
            raise ValueError("Invalid range after alignment")

        return int(start.timestamp()), int(end.timestamp())

    # --------------------------------------------------
    # AVAILABILITY VALIDATION
    # --------------------------------------------------
    def validate_range(self, start_ts, end_ts):
        """
        Ensures requested data exists
        """

        availability = AVAILABILITY_LIMITS[self.interval]

        if availability is None:
            return  # unlimited

        now_ts = int(self._now().timestamp())
        min_allowed = now_ts - availability

        if start_ts < min_allowed:
            raise ValueError(
                f"Data not available for interval {self.interval}. "
                f"Max lookback exceeded."
            )

    # --------------------------------------------------
    # CHUNK DECISION
    # --------------------------------------------------
    def needs_chunking(self, start_ts, end_ts):
        """
        Determines if request exceeds API fetch limits
        """

        limit = FETCH_LIMITS[self.interval]

        if limit is None:
            return False

        return (end_ts - start_ts) > limit

    # --------------------------------------------------
    # PARSING
    # --------------------------------------------------
    def _parse_datetime(self, dt_str: str):
        dt_str = dt_str.strip()

        try:
            dt = datetime.strptime(dt_str, self.format)
        except:
            raise ValueError(
                f"Invalid format. Expected {self.format}"
            )

        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)

        return dt

    # --------------------------------------------------
    # TIME HELPERS
    # --------------------------------------------------
    def _now(self):
        return datetime.now(self.timezone)

    def _floor_to_interval(self, dt: datetime):
        epoch = int(dt.timestamp())
        floored = epoch - (epoch % self.interval_seconds)
        return datetime.fromtimestamp(floored, tz=self.timezone)

if __name__ == "__main__":
    handler = ReqsHandler()

    start_str = "2026-01-01 00:00:00"
    end_str   = "2026-01-16 01:00:00"

    start_ts, end_ts = handler.normalize(start_str, end_str)

    print("Normalized Timestamps:", start_ts, end_ts)

    handler.validate_range(start_ts, end_ts)

    print("Range is valid")

    if handler.needs_chunking(start_ts, end_ts):
        print("Request needs chunking")
    else:
        print("Request can be fetched in one go")