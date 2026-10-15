"""Download public FRED csv files. No API key."""

from __future__ import annotations

import csv
import io
import urllib.request
from datetime import datetime

USER_AGENT = "sksi-credit-stress-index/1.0 (research; +https://github.com/Hossein7935/sksi-credit-stress-index)"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def parse_fred_csv(text: str) -> dict[datetime, float]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        raise ValueError("FRED csv has no data columns")
    date_key = next(name for name in reader.fieldnames if name.lower() in {"date", "observation_date"})
    value_key = next(name for name in reader.fieldnames if name != date_key)
    out: dict[datetime, float] = {}
    for row in reader:
        raw = (row.get(value_key) or "").strip()
        if raw in {"", ".", "nan", "NaN"}:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        out[datetime.strptime(row[date_key][:10], "%Y-%m-%d")] = value
    if not out:
        raise ValueError(f"FRED series {value_key} contained no observations")
    return out


def fetch_fred(series_id: str, timeout: int = 60) -> dict[datetime, float]:
    request = urllib.request.Request(
        FRED_CSV.format(series_id=series_id),
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8")
    return parse_fred_csv(text)


def default_premium(baa: dict[datetime, float], aaa: dict[datetime, float]) -> dict[datetime, float]:
    return {day: baa[day] - aaa[day] for day in sorted(set(baa) & set(aaa))}


def last_on_or_before(
    dates: list[datetime],
    series: dict[datetime, float],
    day: datetime,
    max_age_days: int = 6,
) -> float | None:
    lo, hi = 0, len(dates)
    while lo < hi:
        mid = (lo + hi) // 2
        if dates[mid] <= day:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return None
    found = dates[lo - 1]
    if (day - found).days > max_age_days:
        return None
    return series[found]
