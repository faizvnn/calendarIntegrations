from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .models import CricketMatch, format_label

PRODID = "-//Pakistan Mens Cricket Calendar//Faizan//EN"
CALENDAR_NAME = "Pakistan Men's Cricket"
PUBLISHED_TTL = "PT6H"


def generate_ics(
    matches: Iterable[CricketMatch],
    generated_at: Optional[datetime] = None,
) -> str:
    stamp = _as_utc(generated_at or datetime.now(timezone.utc))
    sorted_matches = sorted(matches, key=lambda match: (match.start, match.match_id))

    lines: List[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_text(CALENDAR_NAME)}",
        "X-WR-TIMEZONE:Etc/UTC",
        f"X-PUBLISHED-TTL:{PUBLISHED_TTL}",
        f"REFRESH-INTERVAL;VALUE=DURATION:{PUBLISHED_TTL}",
    ]

    for match in sorted_matches:
        lines.extend(_event_lines(match, stamp))

    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold_line(line) for line in lines) + "\r\n"


def _event_lines(match: CricketMatch, stamp: datetime) -> List[str]:
    start = _as_utc(match.start)
    end = _as_utc(match.calendar_end())
    status = "CANCELLED" if "cancel" in match.state.lower() else "CONFIRMED"
    location = match.venue.display_name()
    summary = match.summary()
    description_parts = [
        match.series_name,
        f"Format: {format_label(match.match_format)}",
        f"Status: {match.status}" if match.status else "",
        f"Venue: {location}" if location else "",
        f"Source: {match.source_url}" if match.source_url else "Source: Cricbuzz",
    ]
    description = "\n".join(part for part in description_parts if part)

    lines = [
        "BEGIN:VEVENT",
        f"UID:cricbuzz-{match.match_id}@pakistan-mens-cricket-calendar",
        f"DTSTAMP:{_format_dt(stamp)}",
        f"DTSTART:{_format_dt(start)}",
        f"DTEND:{_format_dt(end)}",
        f"SUMMARY:{_escape_text(summary)}",
        f"DESCRIPTION:{_escape_text(description)}",
        f"STATUS:{status}",
        "TRANSP:TRANSPARENT",
        "CATEGORIES:Cricket,Pakistan",
    ]
    if location:
        lines.append(f"LOCATION:{_escape_text(location)}")
    if match.source_url:
        lines.append(f"URL:{match.source_url}")
    lines.append("END:VEVENT")
    return lines


def _format_dt(value: datetime) -> str:
    return _as_utc(value).strftime("%Y%m%dT%H%M%SZ")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_line(line: str, limit: int = 75) -> str:
    if len(line.encode("utf-8")) <= limit:
        return line

    folded: List[str] = []
    current = ""
    current_len = 0
    for char in line:
        char_len = len(char.encode("utf-8"))
        if current and current_len + char_len > limit:
            folded.append(current)
            current = " " + char
            current_len = 1 + char_len
        else:
            current += char
            current_len += char_len

    if current:
        folded.append(current)
    return "\r\n".join(folded)
