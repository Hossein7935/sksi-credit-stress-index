"""SKSI calculation.

The index is a weekly quorum score of four stress legs. Location and scale
were fixed on the calm-enough sample 1997-01-03 through 2006-12-31, before
the global financial crisis, and are not refit as new data arrives.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

KEYS = ("hy", "ig", "def", "nfci")
COMPONENT_WEIGHTS = {"hy": 0.30, "ig": 0.25, "def": 0.25, "nfci": 0.20}
LEVEL_WEIGHT = 0.70
SYNC_WEIGHT = 0.20
ACCEL_WEIGHT = 0.10
QUORUM_Z = 0.75

# Display map. The watch/stress/severe knots come from the frozen 1997–2006
# thresholds so those regimes sit at scores 48, 68 and 84.
def score_knots(calibration: dict) -> tuple[tuple[float, float], ...]:
    median = float(calibration["raw_median"])
    watch = float(calibration["thresholds"]["watch"])
    stress = float(calibration["thresholds"]["stress"])
    severe = float(calibration["thresholds"]["severe"])
    return (
        (median - 1.6, 2.0),
        (median - 1.2, 8.0),
        (median, 28.0),
        (watch, 48.0),
        (stress, 68.0),
        (severe, 84.0),
        (severe + 2.5, 97.0),
        (severe + 6.0, 100.0),
    )


def score_from_raw(raw: float, calibration: dict | None = None) -> float:
    knots = score_knots(calibration or load_calibration())
    if raw <= knots[0][0]:
        return knots[0][1]
    if raw >= knots[-1][0]:
        return knots[-1][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x0 <= raw <= x1:
            weight = (raw - x0) / (x1 - x0)
            value = y0 + weight * (y1 - y0)
            return max(0.0, min(100.0, value))
    return knots[-1][1]


_CALIBRATION_PATH = Path(__file__).with_name("calibration.json")


def load_calibration(path: Path | None = None) -> dict:
    with (path or _CALIBRATION_PATH).open() as handle:
        return json.load(handle)


def zscores(levels: dict[str, float], calibration: dict | None = None) -> dict[str, float]:
    calibration = calibration or load_calibration()
    out = {}
    for key in KEYS:
        anchor = calibration["components"][key]
        out[key] = (float(levels[key]) - float(anchor["median"])) / float(anchor["scale"])
    return out


def regime_from_raw(raw: float, calibration: dict | None = None) -> str:
    calibration = calibration or load_calibration()
    cuts = calibration["thresholds"]
    if raw >= float(cuts["severe"]):
        return "severe"
    if raw >= float(cuts["stress"]):
        return "stress"
    if raw >= float(cuts["watch"]):
        return "watch"
    return "normal"


def state_from_z(z: float) -> str:
    if z < -0.5:
        return "niedrig"
    if z < QUORUM_Z:
        return "normal"
    if z < 1.5:
        return "erhöht"
    return "stark"


def combine(
    levels: dict[str, float],
    prev_z: dict[str, float] | None = None,
    calibration: dict | None = None,
) -> dict:
    """Score one week.

    `prev_z` is the z-score vector from four weeks earlier. It is optional so a
    single current reading still works; without it the acceleration term is zero.
    """
    calibration = calibration or load_calibration()
    z = zscores(levels, calibration)
    level = sum(COMPONENT_WEIGHTS[key] * z[key] for key in KEYS)
    sync = min(z[key] for key in KEYS)
    if prev_z is None:
        accel = 0.0
    else:
        accel = sum(max(0.0, z[key] - float(prev_z[key])) for key in KEYS) / 4.0
    raw = LEVEL_WEIGHT * level + SYNC_WEIGHT * max(sync, 0.0) + ACCEL_WEIGHT * accel
    regime = regime_from_raw(raw, calibration)
    quorum = sync >= QUORUM_Z and regime in {"stress", "severe"}
    scored = score_from_raw(raw, calibration)
    return {
        "raw": raw,
        "score": scored,
        "regime": regime,
        "quorum": quorum,
        "z": z,
        "level": level,
        "sync": sync,
        "accel": accel,
    }


REGIME_DE = {
    "normal": "Ruhig",
    "watch": "Erhöht",
    "stress": "Stress",
    "severe": "Schwer",
}

COMPONENT_DE = {
    "hy": "High-Yield-OAS",
    "ig": "Investment-Grade-OAS",
    "def": "Ausfallprämie (Baa−Aaa)",
    "nfci": "NFCI",
}


def summarize(result: dict) -> str:
    hot = [COMPONENT_DE[key] for key in KEYS if result["z"][key] >= QUORUM_Z]
    tight_credit = all(result["z"][key] < -0.5 for key in ("hy", "ig", "def"))
    label = REGIME_DE[result["regime"]]
    if result["regime"] == "normal" and not hot and tight_credit:
        text = (
            f"{label}. Die Kreditaufschläge liegen unter ihrem normalen Niveau von 1997–2006, "
            "und es gibt kein Quorum für Stress."
        )
    elif result["regime"] == "normal" and not hot:
        text = f"{label}. Keiner der vier Bausteine liegt deutlich über seinem Niveau von 1997–2006."
    elif result["regime"] == "normal":
        text = f"{label}, aber schon erhöht: {', '.join(hot)}."
    elif result["regime"] == "watch":
        text = f"{label}. Kreditbedingungen spannen sich an ({', '.join(hot) or 'noch ohne klares Quorum'})."
    elif result["regime"] == "stress":
        text = f"{label}. Deutlicher Kreditstress ({', '.join(hot) or 'gemischt'})."
    else:
        text = f"{label}. Schwerer Kreditstress, vergleichbar mit den großen Ausweitungen seit 2007."
    if result["quorum"]:
        text += " Quorum: alle vier Signale sind gleichzeitig erhöht."
    return text


def as_of(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]
