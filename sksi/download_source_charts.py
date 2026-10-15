"""Regenerate local SVG source charts from the same public FRED data as SKSI."""
from __future__ import annotations

import html
import shutil
from datetime import date
from pathlib import Path

from .update import fetch_series

ROOT = Path(__file__).resolve().parent.parent
CHARTS = {
    "hy": ("ICE BofA US High Yield Index Option-Adjusted Spread", "High-Yield OAS", "#c026d3"),
    "ig": ("ICE BofA US Corporate Index Option-Adjusted Spread", "Investment-Grade OAS", "#0284c7"),
    "def": ("Moody's Baa minus Aaa Corporate Bond Yield", "Baa − Aaa spread", "#ea580c"),
    "nfci": ("Chicago Fed National Financial Conditions Index", "NFCI", "#059669"),
}


def svg_chart(title: str, label: str, color: str,
              rows: list[tuple[date, float]]) -> str:
    width, height = 1000, 360
    left, right, top, bottom = 78, 28, 46, 44
    plot_w, plot_h = width - left - right, height - top - bottom
    if len(rows) < 2:
        raise RuntimeError(f"Not enough observations for chart: {title}")
    values = [v for _, v in rows]
    low, high = min(values), max(values)
    padding = (high - low) * 0.08 if high > low else 1.0
    low, high = low - padding, high + padding
    start, end = rows[0][0], rows[-1][0]
    span = max((end - start).days, 1)

    def x(dt: date) -> float:
        return left + ((dt - start).days / span) * plot_w

    def y(value: float) -> float:
        return top + (high - value) / (high - low) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect width="100%" height="100%" rx="12" fill="#ffffff"/>',
        f'<text x="{left}" y="25" font-family="Arial,sans-serif" font-size="17" font-weight="600" fill="#182538">{html.escape(title)}</text>',
    ]
    for i in range(5):
        value = low + (high - low) * i / 4
        yy = y(value)
        parts.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{width-right}" y2="{yy:.2f}" stroke="#e3e9f0" stroke-width="1"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="#53657a">{value:.2f}</text>')
    step = 5 if end.year - start.year > 12 else 2
    for year in range(start.year, end.year + 1):
        if (year - start.year) % step and year != end.year:
            continue
        dt = date(year, 1, 1)
        if dt < start or dt > end:
            continue
        xx = x(dt)
        parts.append(f'<line x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{height-bottom}" stroke="#f0f3f7" stroke-width="1"/>')
        parts.append(f'<text x="{xx:.2f}" y="{height-16}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" fill="#53657a">{year}</text>')
    points = " ".join(f"{x(dt):.2f},{y(value):.2f}" for dt, value in rows)
    parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="{points}"/>')
    parts.append(f'<line x1="{left}" y1="{height-17}" x2="{left+20}" y2="{height-17}" stroke="{color}" stroke-width="3"/>')
    parts.append(f'<text x="{left+27}" y="{height-13}" font-family="Arial,sans-serif" font-size="12" fill="#53657a">{html.escape(label)}</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    # Use the exact same official FRED series fetcher as the SKSI calculation.
    series = fetch_series()
    for key, (title, label, color) in CHARTS.items():
        rows = sorted((dt.date(), float(value)) for dt, value in series[key].items())
        content = svg_chart(title, label, color, rows)
        root_chart = ROOT / "charts" / f"{key}.svg"
        docs_chart = ROOT / "docs" / "charts" / f"{key}.svg"
        root_chart.parent.mkdir(parents=True, exist_ok=True)
        root_chart.write_text(content, encoding="utf-8")
        docs_chart.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root_chart, docs_chart)
        print(f"Updated {key} chart with {len(rows)} FRED observations")


if __name__ == "__main__":
    main()
