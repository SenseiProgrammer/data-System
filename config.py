# pyconfig.py

# -----------------------------
# TIME CONFIG
# -----------------------------
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMEZONE = "Asia/Kolkata"

# -----------------------------
# INTERVAL MAP (canonical)
# -----------------------------
INTERVAL_MAP = {
    "1m": 60,
    "2m": 120,
    "3m": 180,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800
}

DEFAULT_INTERVAL = "5m"

# -----------------------------
# DATA AVAILABILITY LIMITS
# (safe approximation based on Groww behavior)
# -----------------------------
AVAILABILITY_LIMITS = {
    "1m": 90 * 86400,
    "2m": 90 * 86400,
    "3m": 90 * 86400,
    "5m": 180 * 86400,
    "10m": 365 * 86400,
    "15m": 365 * 86400,
    "30m": 365 * 86400,
    "1h": 365 * 86400,
    "4h": 3 * 365 * 86400,
    "1d": None,   # full history
    "1w": None
}

# -----------------------------
# FETCH LIMITS PER REQUEST
# (safe conservative limits)
# -----------------------------
FETCH_LIMITS = {
    "1m": 7 * 86400,
    "2m": 7 * 86400,
    "3m": 7 * 86400,
    "5m": 15 * 86400,
    "10m": 30 * 86400,
    "15m": 30 * 86400,
    "30m": 30 * 86400,
    "1h": 150 * 86400,
    "4h": 365 * 86400,
    "1d": 1080 * 86400,
    "1w": None
}