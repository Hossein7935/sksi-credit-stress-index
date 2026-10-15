"""Dependency-free SVG of the weekly SKSI score."""

from __future__ import annotations


def render_svg(rows: list[dict]) -> str:
    width, height = 960, 360
    left, right, top, bottom = 48, 16, 28, 36
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x_of(index: int) -> float:
        if len(rows) == 1:
            return left
        return left + plot_w * index / (len(rows) - 1)

    def y_of(score: float) -> float:
        return top + plot_h * (1.0 - max(0.0, min(100.0, score)) / 100.0)

    points = " ".join(f"{x_of(i):.1f},{y_of(float(row['score'])):.1f}" for i, row in enumerate(rows))
    bands = (
        (48, 68, "#f4e4c4", "Erhöht 48"),
        (68, 84, "#f3d2b5", "Stress 68"),
        (84, 100, "#f0c2c2", "Schwer 84"),
    )
    band_svg = []
    for lo, hi, color, _label in bands:
        y = y_of(hi)
        h = y_of(lo) - y
        band_svg.append(f'<rect x="{left}" y="{y:.1f}" width="{plot_w}" height="{h:.1f}" fill="{color}"/>')

    guides = []
    for level, label in ((48, "48"), (68, "68"), (84, "84")):
        y = y_of(level)
        guides.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#8a8175" stroke-dasharray="3 4" stroke-width="1"/>'
            f'<text x="{left - 6}" y="{y + 3:.1f}" text-anchor="end" font-size="11" fill="#5c564e">{label}</text>'
        )

    start = rows[0]["date"][:4]
    end = rows[-1]["date"][:4]
    last = rows[-1]
    title = "SKSI — Synchronisierter Kreditstress-Index"
    subtitle = f"{start}–{end} · letzter Stand {last['date']} · {float(last['score']):.0f} ({last['regime']})"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">
  <title>{title}</title>
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <text x="{left}" y="18" font-family="Georgia, serif" font-size="16" fill="#1f1c18">{title}</text>
  <text x="{width - right}" y="18" text-anchor="end" font-family="Georgia, serif" font-size="12" fill="#5c564e">{subtitle}</text>
  {''.join(band_svg)}
  {''.join(guides)}
  <polyline fill="none" stroke="#1f4d3a" stroke-width="1.6" points="{points}"/>
  <text x="{left}" y="{height - 12}" font-family="Georgia, serif" font-size="11" fill="#5c564e">Wochenwerte, NFCI-Takt. Bänder: erhöht ab 48, Stress ab 68, schwer ab 84.</text>
</svg>
"""
