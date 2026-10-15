"""Refresh the weekly index from FRED and rewrite data/latest.json."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from .chart import render_svg
from .fetch import default_premium, fetch_fred, last_on_or_before
from .model import (
    COMPONENT_DE,
    KEYS,
    as_of,
    combine,
    state_from_z,
    summarize,
    zscores,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "data" / "sksi_weekly.csv"
LATEST_JSON = ROOT / "data" / "latest.json"
CHART_SVG = ROOT / "docs" / "history.svg"
FIELDS = ["date", "score", "regime", "quorum", "raw"]


def load_history(path: Path = DATA_CSV) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["score"] = float(row["score"])
        row["raw"] = float(row["raw"])
        row["quorum"] = str(row["quorum"]).lower() in {"1", "true", "yes"}
    return rows


def write_history(rows: list[dict], path: Path = DATA_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "score": f"{float(row['score']):.2f}",
                    "regime": row["regime"],
                    "quorum": "1" if row["quorum"] else "0",
                    "raw": f"{float(row['raw']):.6f}",
                }
            )


def matched_weeks(series: dict[str, dict[datetime, float]]) -> list[dict]:
    nfci_dates = sorted(series["nfci"])
    lookup = {key: sorted(series[key]) for key in ("hy", "ig", "def")}
    weeks = []
    for day in nfci_dates:
        if day < datetime(1997, 1, 3):
            continue
        levels = {"nfci": series["nfci"][day]}
        missing = False
        for key in ("hy", "ig", "def"):
            value = last_on_or_before(lookup[key], series[key], day, 6)
            if value is None:
                missing = True
                break
            levels[key] = value
        if missing:
            continue
        weeks.append({"date": day, "levels": levels})
    return weeks


def merge(history: list[dict], fresh: list[dict]) -> list[dict]:
    """Recompute a fresh week only when its four-week lag is in the fresh sample.

    Older history stays as published. FRED serves only a rolling window of the
    ICE spread series, so the long backtest cannot be rebuilt from the live API.
    """
    hist = {row["date"]: row for row in history}
    fresh_by_date = {as_of(week["date"]): week for week in fresh}
    fresh_dates = [as_of(week["date"]) for week in fresh]
    fresh_index = {day: index for index, day in enumerate(fresh_dates)}
    merged = []
    for day in sorted(set(hist) | set(fresh_by_date)):
        index = fresh_index.get(day)
        if index is None or index < 4:
            if day in hist:
                merged.append(hist[day])
            continue
        lag_levels = fresh_by_date[fresh_dates[index - 4]]["levels"]
        current = combine(fresh_by_date[day]["levels"], prev_z=zscores(lag_levels))
        merged.append(
            {
                "date": day,
                "score": current["score"],
                "regime": current["regime"],
                "quorum": current["quorum"],
                "raw": current["raw"],
            }
        )
    return merged


def build_latest(scored_row: dict, week: dict) -> dict:
    result = combine(week["levels"], prev_z=None)
    result["score"] = float(scored_row["score"])
    result["regime"] = scored_row["regime"]
    result["quorum"] = bool(scored_row["quorum"])
    result["raw"] = float(scored_row["raw"])
    components = {
        key: {
            "name": COMPONENT_DE[key],
            "value": round(float(week["levels"][key]), 4),
            "z": round(result["z"][key], 3),
            "state": state_from_z(result["z"][key]),
        }
        for key in KEYS
    }
    return {
        "date": scored_row["date"],
        "score": round(float(scored_row["score"]), 2),
        "regime": scored_row["regime"],
        "quorum": bool(scored_row["quorum"]),
        "raw": round(float(scored_row["raw"]), 6),
        "components": components,
        "summary": summarize(result),
        "disclaimer": "Informationssignal, keine Anlageberatung und keine Garantie künftiger Krisen.",
    }


def fetch_series() -> dict[str, dict[datetime, float]]:
    hy = fetch_fred("BAMLH0A0HYM2")
    ig = fetch_fred("BAMLC0A0CM")
    baa = fetch_fred("DBAA")
    aaa = fetch_fred("DAAA")
    nfci = fetch_fred("NFCI")
    return {"hy": hy, "ig": ig, "def": default_premium(baa, aaa), "nfci": nfci}


def refresh(history: list[dict] | None = None) -> tuple[list[dict], dict]:
    series = fetch_series()
    fresh = matched_weeks(series)
    if len(fresh) < 8:
        raise RuntimeError(f"only {len(fresh)} usable weeks fetched; refusing to update")
    merged = merge(history if history is not None else load_history(), fresh)
    if not merged:
        raise RuntimeError("update produced an empty history")
    last_day = as_of(fresh[-1]["date"])
    scored = next(row for row in merged if row["date"] == last_day)
    latest = build_latest(scored, fresh[-1])
    return merged, latest


def main() -> int:
    merged, latest = refresh()
    write_history(merged)
    LATEST_JSON.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n")
    CHART_SVG.parent.mkdir(parents=True, exist_ok=True)
    CHART_SVG.write_text(render_svg(merged))
    print(
        f"{latest['date']}  SKSI {latest['score']:.1f}  {latest['regime']}"
        f"  quorum={str(latest['quorum']).lower()}"
    )
    print(latest["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
