from datetime import datetime
import os
import csv
import pytz

from config import (
    DATETIME_FORMAT,
    TIMEZONE,
    INTERVAL_MAP,
    DEFAULT_INTERVAL,
    AVAILABILITY_LIMITS,
    FETCH_LIMITS,
)


class TsStr(str):
    """
    Timestamp string with a convenience method:
    TsStr("1724457600").ts_to_dt()
    """

    def ts_to_dt(self):
        ts = int(self)

        tz = pytz.timezone(TIMEZONE)
        dt = datetime.fromtimestamp(ts, tz=tz)
        return dt.strftime(DATETIME_FORMAT)


class ReqsHandler:
    """
    Handles:
    - datetime parsing
    - normalization
    - availability validation
    - chunk decision
    - chunk planning
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
        Returns normalized timestamp strings:
        {
            "start_ts": TsStr(...),
            "end_ts": TsStr(...)
        }
        """

        start = self._parse_datetime(start_str)
        end = self._parse_datetime(end_str)

        now = self._now()

        # Clamp future end to now
        if end > now:
            end = now

        # Floor to last completed candle
        start = self._floor_to_interval(start)
        end = self._floor_to_interval(end)

        if start >= end:
            raise ValueError("Invalid range after alignment")

        return {
            "start_ts": TsStr(str(int(start.timestamp()))),
            "end_ts": TsStr(str(int(end.timestamp()))),
        }

    # --------------------------------------------------
    # AVAILABILITY VALIDATION
    # --------------------------------------------------
    def validate_range(self, start_ts, end_ts):
        """
        Raises error if requested start is older than available history.
        """
        start_ts = self._to_int(start_ts)
        end_ts = self._to_int(end_ts)

        rule = AVAILABILITY_LIMITS[self.interval]

        if rule is None:
            return

        now = self._now()
        now_ts = int(now.timestamp())

        if isinstance(rule, int):
            min_allowed_ts = now_ts - rule
        else:
            # Example: {"since_year": 2020}
            since_year = int(rule["since_year"])
            min_allowed_dt = self.timezone.localize(
                datetime(since_year, 1, 1, 0, 0, 0)
            )
            min_allowed_ts = int(min_allowed_dt.timestamp())

        if start_ts < min_allowed_ts:
            raise ValueError(
                f"Requested range exceeds available history for interval {self.interval}"
            )

        if end_ts <= start_ts:
            raise ValueError("Invalid range: end must be greater than start")

    # --------------------------------------------------
    # CHUNK NEED DECISION
    # --------------------------------------------------
    def needs_chunking(self, start_ts, end_ts):
        """
        Returns True if request exceeds per-request fetch limit.
        """
        start_ts = self._to_int(start_ts)
        end_ts = self._to_int(end_ts)

        limit = FETCH_LIMITS[self.interval]

        if limit is None:
            return False

        return (end_ts - start_ts) > limit

    # --------------------------------------------------
    # CHUNK PLANNER
    # --------------------------------------------------
    def chunk_planner(self, start_ts, end_ts):
        """
        Returns:
        {
            "needs_chunking": bool,
            "chunk_count": int,
            "chunks": [
                {"start_ts": TsStr(...), "end_ts": TsStr(...)},
                ...
            ]
        }
        """
        start_ts = self._to_int(start_ts)
        end_ts = self._to_int(end_ts)

        self.validate_range(start_ts, end_ts)

        limit = FETCH_LIMITS[self.interval]

        # No chunking needed
        if limit is None or (end_ts - start_ts) <= limit:
            return {
                "needs_chunking": False,
                "chunk_count": 1,
                "chunks": [
                    {
                        "start_ts": TsStr(str(start_ts)),
                        "end_ts": TsStr(str(end_ts)),
                    }
                ],
            }

        # Chunking needed
        chunks = []
        current = start_ts

        while current < end_ts:
            next_end = min(current + limit, end_ts)

            chunks.append(
                {
                    "start_ts": TsStr(str(current)),
                    "end_ts": TsStr(str(next_end)),
                }
            )

            current = next_end

        return {
            "needs_chunking": True,
            "chunk_count": len(chunks),
            "chunks": chunks,
        }
    
    # --------------------------------------------------
    # CSV FILE CHECK
    # --------------------------------------------------
    def is_csv(self, exchange: str, stock: str, interval: str):
        base_dir = os.getcwd()
        dir_path = os.path.join(base_dir, "historical", exchange, stock)
        file_name = f"{interval}_data.csv"
        file_path = os.path.join(dir_path, file_name)

        os.makedirs(dir_path, exist_ok=True)

        # UPDATED HEADERS
        required_headers = [
            "timestamp",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        status = {
            "path": file_path,
            "exists": False,
            "has_headers": False,
            "has_data": False,
            "created": False,
            "recreated": False
        }

        # ----------------------------
        # FILE NOT EXISTS → CREATE
        # ----------------------------
        if not os.path.isfile(file_path):
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(required_headers)

            status.update({
                "has_headers": True,
                "created": True
            })
            return status

        status["exists"] = True

        # ----------------------------
        # VALIDATE FILE
        # ----------------------------
        try:
            with open(file_path, "r", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if not rows:
                raise ValueError("Empty file")

            headers = [h.strip().lower() for h in rows[0]]

            if headers != required_headers:
                raise ValueError("Invalid headers")

            status["has_headers"] = True

            # Check for data rows
            if len(rows) > 1:
                for row in rows[1:]:
                    if any(cell.strip() for cell in row):
                        status["has_data"] = True
                        break

        except Exception:
            # ----------------------------
            # RECREATE FILE
            # ----------------------------
            try:
                os.remove(file_path)
            except Exception:
                pass

            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(required_headers)

            status.update({
                "has_headers": True,
                "recreated": True
            })

            return status

        return status

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------
    def _parse_datetime(self, dt_str: str):
        dt_str = dt_str.strip()

        try:
            dt = datetime.strptime(dt_str, self.format)
        except Exception:
            raise ValueError(f"Invalid format. Expected {self.format}")

        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)

        return dt

    def _now(self):
        return datetime.now(self.timezone)

    def _floor_to_interval(self, dt: datetime):
        epoch = int(dt.timestamp())
        floored = epoch - (epoch % self.interval_seconds)
        return datetime.fromtimestamp(floored, tz=self.timezone)

    def _to_int(self, value):
        if isinstance(value, TsStr):
            return int(value)
        if isinstance(value, str):
            return int(value)
        return int(value)

#--------------------------------------------------
#------------Usage Example-------------------------
if __name__ == "__main__":
    handler = ReqsHandler(interval="5m")

    start_dt = "2026-01-01 00:00:00"
    end_dt = "2026-04-04 00:00:00"

    # Example usage
    normalized = handler.normalize(start_dt, end_dt)
    print("Normalized:", normalized)

    handler.validate_range(normalized["start_ts"], normalized["end_ts"])
    print("Range is valid")

    needs_chunking = handler.needs_chunking(normalized["start_ts"], normalized["end_ts"])
    print("Needs chunking:", needs_chunking)

    chunk_plan = handler.chunk_planner(normalized["start_ts"], normalized["end_ts"])
    print("Chunk plan:", chunk_plan)
    
    csv_status = handler.is_csv("Nse","TCS","5m")
    print("CSV STATUS : ", csv_status)
