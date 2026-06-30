from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .calendar import generate_ics
from .cricbuzz import DEFAULT_SOURCE_URL, fetch_matches
from .filters import filter_pakistan_mens_matches


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export Pakistan men's cricket fixtures as an ICS file.")
    parser.add_argument("--output", default="dist/pakistan-men.ics", help="Output .ics path")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL, help="Cricbuzz schedule URL")
    parser.add_argument("--include-past", action="store_true", help="Include past matches")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    raw_matches = fetch_matches(args.source_url)
    matches = filter_pakistan_mens_matches(raw_matches, now=now, include_past=args.include_past)
    ics = generate_ics(matches, generated_at=now)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        file.write(ics)

    print(f"Wrote {len(matches)} matches to {output}")
    for match in matches:
        print(f"- {match.start.date().isoformat()} {match.summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
