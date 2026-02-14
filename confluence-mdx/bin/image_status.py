#!/usr/bin/env python3
"""
Docker image var/ data status report.

Scans var/ directory to produce a summary of page data freshness:
- Image build date
- fetch_state.yaml info
- Page count and version statistics
- Oldest pages (stale data candidates)

Usage:
  bin/image_status.py [--var-dir VAR] [--top N]
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def read_build_date(workdir: Path) -> str:
    """Read image build date from .build-date file."""
    build_date_file = workdir / ".build-date"
    if build_date_file.exists():
        return build_date_file.read_text().strip()
    return "unknown"


def read_fetch_state(var_dir: Path) -> dict:
    """Find and read fetch_state.yaml."""
    for state_file in var_dir.glob("*/fetch_state.yaml"):
        with open(state_file) as f:
            return yaml.safe_load(f) or {}
    return {}


def scan_pages(var_dir: Path) -> list[dict]:
    """Scan all page.v2.yaml files and extract version metadata."""
    pages = []
    for page_dir in sorted(var_dir.iterdir()):
        if not page_dir.is_dir() or not page_dir.name.isdigit():
            continue
        v2_file = page_dir / "page.v2.yaml"
        if not v2_file.exists():
            continue
        try:
            with open(v2_file) as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            version_info = data.get("version", {})
            pages.append({
                "page_id": page_dir.name,
                "title": data.get("title", "?"),
                "version": version_info.get("number", "?"),
                "created_at": version_info.get("createdAt", ""),
            })
        except Exception:
            logging.warning("Failed to parse %s, skipping", v2_file)
            continue
    return pages


def parse_iso(date_str: str) -> datetime | None:
    """Parse ISO 8601 date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_report(workdir: Path, var_dir: Path, top_n: int) -> str:
    """Generate the status report."""
    lines: list[str] = []

    # Header
    lines.append("# ── Image Status Report ──────────────────────")

    # Build date
    build_date = read_build_date(workdir)
    lines.append(f"  Build Date       : {build_date}")

    # Fetch state
    state = read_fetch_state(var_dir)
    if state:
        lines.append(f"  Last Modified    : {state.get('last_modified_seen', '?')}")
        lines.append(f"  Last Recent Fetch: {state.get('last_recent_fetch', '?')}")
        lines.append(f"  Last Full Fetch  : {state.get('last_full_fetch', '?')}")
        lines.append(f"  Pages Fetched    : {state.get('pages_fetched', '?')}")
    else:
        lines.append("  Fetch State      : not found")

    # Scan pages
    pages = scan_pages(var_dir)
    lines.append(f"  Pages in var/    : {len(pages)}")

    if not pages:
        lines.append("# ─────────────────────────────────────────────")
        return "\n".join(lines)

    # Parse dates and compute stats
    dated_pages = []
    for p in pages:
        dt = parse_iso(p["created_at"])
        if dt:
            dated_pages.append((dt, p))

    if dated_pages:
        dated_pages.sort(key=lambda x: x[0])
        oldest_dt = dated_pages[0][0]
        newest_dt = dated_pages[-1][0]
        lines.append(f"  Oldest Version   : {oldest_dt.strftime('%Y-%m-%d %H:%M')} UTC")
        lines.append(f"  Newest Version   : {newest_dt.strftime('%Y-%m-%d %H:%M')} UTC")

        # Age distribution
        now = datetime.now(timezone.utc)
        buckets = {"< 1 day": 0, "1-7 days": 0, "7-30 days": 0, "30-90 days": 0, "> 90 days": 0}
        for dt, _ in dated_pages:
            age_days = (now - dt).days
            if age_days < 1:
                buckets["< 1 day"] += 1
            elif age_days < 7:
                buckets["1-7 days"] += 1
            elif age_days < 30:
                buckets["7-30 days"] += 1
            elif age_days < 90:
                buckets["30-90 days"] += 1
            else:
                buckets["> 90 days"] += 1

        lines.append("")
        lines.append("  Age Distribution:")
        for label, count in buckets.items():
            if count > 0:
                bar = "#" * min(count, 50)
                lines.append(f"    {label:>10s} : {count:3d}  {bar}")

        # Oldest pages (stale candidates)
        lines.append("")
        lines.append(f"  Oldest {top_n} Pages (stale candidates):")
        for dt, p in dated_pages[:top_n]:
            age = (now - dt).days
            lines.append(f"    [{p['page_id']}] v{p['version']} ({age}d ago) {p['title']}")

    lines.append("# ─────────────────────────────────────────────")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Docker image var/ data status report")
    parser.add_argument("--workdir", default="/workdir", help="Working directory (default: /workdir)")
    parser.add_argument("--var-dir", default=None, help="var/ directory path (default: <workdir>/var)")
    parser.add_argument("--top", type=int, default=10, help="Number of oldest pages to show (default: 10)")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    var_dir = Path(args.var_dir) if args.var_dir else workdir / "var"

    if not var_dir.is_dir():
        print(f"ERROR: var/ directory not found: {var_dir}", file=sys.stderr)
        sys.exit(1)

    print(format_report(workdir, var_dir, args.top))


if __name__ == "__main__":
    main()
