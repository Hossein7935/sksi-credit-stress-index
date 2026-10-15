"""Regenerate local SVG source charts from the same public FRED data as SKSI."""
from __future__ import annotations

import html
import shutil
from datetime import date
from pathlib import Path

from .update import fetch_series

ROOT = Path(__file__).resolve().parent.parent
CHARTS = {
    "hy": ("ICE BofA US High Yield Index Option-Adjusted Spread", "High-Yield OAS", "#60a5fa"),
    "ig": ("ICE BofA US Corporate Index Option-Adjusted Spread", "Investment-Grade OAS", "#60a5fa"),
    "def": ("Moody's Baa minus Aaa Corporate Bond Yield", "Baa − Aaa spread", "#60a5fa"),
    "nfci": ("Chicago Fed National Financial Conditions Index", "NFCI", "#60a5fa"),
}

# Official US recession periods according to NBER, shown with the same
# peak-to-trough date convention used for recession shading on FRED charts.
RECESSIONS = [
    ("2001-03-01", "2001-11-01", "2001 recession"),
    ("2007-12-01", "2009-06-01", "Great Recession"),
    ("2020-02-01", "2020-04-01", "COVID-19 recession"),
]


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
    # Keep SVGs light enough for fast mobile loading while retaining the full
    # date range and value range. Each plotted sample remains hoverable.
    max_points = 800
    stride = max(1, (len(rows) + max_points - 1) // max_points)
    plot_rows = rows[::stride]
    if plot_rows[-1] != rows[-1]:
        plot_rows.append(rows[-1])
    start, end = rows[0][0], rows[-1][0]
    span = max((end - start).days, 1)

    def x(dt: date) -> float:
        return left + ((dt - start).days / span) * plot_w

    def y(value: float) -> float:
        return top + (high - value) / (high - low) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect class="mini-bg" width="100%" height="100%" rx="12" fill="#0b1422"/>',
        f'<text x="{left}" y="25" font-family="Arial,sans-serif" font-size="17" font-weight="600" class="mini-text" fill="#a7b6ca">{html.escape(title)}</text>',
    ]
    # Shade each US recession that overlaps this chart's data range.
    for recession_start, recession_end, recession_label in RECESSIONS:
        rec_start = date.fromisoformat(recession_start)
        rec_end = date.fromisoformat(recession_end)
        visible_start, visible_end = max(start, rec_start), min(end, rec_end)
        if visible_start <= visible_end:
            x1, x2 = x(visible_start), x(visible_end)
            parts.append(
                f'<rect x="{x1:.2f}" y="{top}" width="{max(1, x2-x1):.2f}" '
                f'height="{plot_h}" fill="#ef4444" fill-opacity="0.16">'
                f'<title>{html.escape(recession_label)}: {visible_start:%b %Y} – {visible_end:%b %Y}</title></rect>'
            )
    for i in range(5):
        value = low + (high - low) * i / 4
        yy = y(value)
        parts.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{width-right}" y2="{yy:.2f}" class="mini-grid" stroke="#26364a" stroke-width="1"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" class="mini-text" fill="#a7b6ca">{value:.2f}</text>')
    step = 5 if end.year - start.year > 12 else 2
    for year in range(start.year, end.year + 1):
        if (year - start.year) % step and year != end.year:
            continue
        dt = date(year, 1, 1)
        if dt < start or dt > end:
            continue
        xx = x(dt)
        parts.append(f'<line x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{height-bottom}" class="mini-vgrid" stroke="#1d2b3e" stroke-width="1"/>')
        parts.append(f'<text x="{xx:.2f}" y="{height-16}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" class="mini-text" fill="#a7b6ca">{year}</text>')
    points = " ".join(f"{x(dt):.2f},{y(value):.2f}" for dt, value in plot_rows)
    parts.append(f'<polyline fill="none" class="mini-line" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="{points}"/>')
    # Invisible but hoverable data points show the exact date and value.
    for dt, value in plot_rows:
        parts.append(
            f'<circle cx="{x(dt):.2f}" cy="{y(value):.2f}" r="5" '
            f'fill="{color}" fill-opacity="0.001" stroke="none" pointer-events="all">'
            f'<title>{dt:%d %b %Y}: {value:.4f}</title></circle>'
        )
    legend_y = height - 17
    parts.append(f'<line x1="{left}" y1="{legend_y}" x2="{left+20}" y2="{legend_y}" class="mini-line" stroke="{color}" stroke-width="3"/>')
    parts.append(f'<text x="{left+27}" y="{height-13}" font-family="Arial,sans-serif" font-size="12" class="mini-text" fill="#a7b6ca">{html.escape(label)}</text>')
    parts.append(f'<rect x="{left+260}" y="{legend_y-5}" width="18" height="10" fill="#ef4444" fill-opacity="0.25"/>')
    parts.append(f'<text x="{left+284}" y="{height-13}" font-family="Arial,sans-serif" font-size="12" class="mini-text" fill="#a7b6ca">US recession</text>')
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
