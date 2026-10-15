"""Download current FRED chart images for the four SKSI source cards.

Images are stored locally so the website does not depend on browser-side
hotlinking or third-party image caching. Run on every SKSI data refresh.
"""
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
START = "1997-01-01"
CHARTS = {
    "hy": ("BAMLH0A0HYM2", "ICE BofA US High Yield Index Option-Adjusted Spread"),
    "ig": ("BAMLC0A0CM", "ICE BofA US Corporate Index Option-Adjusted Spread"),
    "def": ("DBAA,DAAA", "Moody's Baa and Aaa Corporate Bond Yields"),
    "nfci": ("NFCI", "Chicago Fed National Financial Conditions Index"),
}


def download(series: str, title: str, destination: Path) -> None:
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.png"
        f"?id={series}&cosd={START}&width=1000&height=360"
    )
    request = Request(
        url,
        headers={"User-Agent": "SKSI-Credit-Stress-Index/1.0 (source chart updater)"},
    )
    with urlopen(request, timeout=45) as response:
        image = response.read()
        content_type = response.headers.get("Content-Type", "")
    if not image.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(
            f"FRED did not return a PNG for {series} "
            f"(Content-Type: {content_type}; bytes: {len(image)})"
        )
    if len(image) < 5_000:
        raise RuntimeError(f"FRED chart for {series} is unexpectedly small ({len(image)} bytes)")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image)
    print(f"Downloaded {title}: {destination} ({len(image):,} bytes)")


def main() -> None:
    for key, (series, title) in CHARTS.items():
        # Save in both supported GitHub Pages layouts (repository root or /docs).
        download(series, title, ROOT / "charts" / f"{key}.png")
        download(series, title, ROOT / "docs" / "charts" / f"{key}.png")


if __name__ == "__main__":
    main()
