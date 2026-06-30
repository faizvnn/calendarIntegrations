from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from .models import CricketMatch, Team, Venue

DEFAULT_SOURCE_URL = "https://www.cricbuzz.com/cricket-team/pakistan/3/schedule"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


class CricbuzzParseError(RuntimeError):
    pass


def fetch_schedule_html(url: str = DEFAULT_SOURCE_URL, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def fetch_matches(url: str = DEFAULT_SOURCE_URL, timeout: int = 20) -> List[CricketMatch]:
    html = fetch_schedule_html(url=url, timeout=timeout)
    return extract_matches_from_html(html)


def extract_matches_from_html(html: str) -> List[CricketMatch]:
    flight_payload = "\n".join(_iter_next_flight_strings(html))
    if not flight_payload:
        raise CricbuzzParseError("Could not find Cricbuzz Next.js data chunks.")

    matches: List[CricketMatch] = []
    seen = set()
    for match_info in _extract_json_objects_after_key(flight_payload, '"matchInfo":'):
        match = _parse_match_info(match_info)
        if match.match_id in seen:
            continue
        seen.add(match.match_id)
        matches.append(match)

    if not matches:
        raise CricbuzzParseError("Could not find any matchInfo objects in Cricbuzz data.")
    return matches


def _iter_next_flight_strings(html: str) -> Iterator[str]:
    marker = "self.__next_f.push([1,"
    cursor = 0
    while True:
        start = html.find(marker, cursor)
        if start == -1:
            return
        quote = html.find('"', start + len(marker))
        if quote == -1:
            cursor = start + len(marker)
            continue
        end = _find_json_string_end(html, quote)
        if end == -1:
            cursor = quote + 1
            continue

        literal = html[quote : end + 1]
        try:
            yield json.loads(literal)
        except json.JSONDecodeError:
            pass
        cursor = end + 1


def _find_json_string_end(text: str, quote_index: int) -> int:
    escaped = False
    for index in range(quote_index + 1, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return index
    return -1


def _extract_json_objects_after_key(text: str, key: str) -> Iterator[dict]:
    cursor = 0
    while True:
        key_index = text.find(key, cursor)
        if key_index == -1:
            return
        object_start = text.find("{", key_index + len(key))
        if object_start == -1:
            return
        object_end = _find_matching_brace(text, object_start)
        if object_end == -1:
            cursor = object_start + 1
            continue

        raw_object = text[object_start : object_end + 1]
        try:
            yield json.loads(raw_object)
        except json.JSONDecodeError:
            pass
        cursor = object_end + 1


def _find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    escaped = False

    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _parse_match_info(info: dict) -> CricketMatch:
    match_id = _int_value(info.get("matchId"))
    start = _epoch_ms_to_datetime(info.get("startDate"))
    if start is None:
        raise CricbuzzParseError(f"Match {match_id} is missing startDate.")

    return CricketMatch(
        match_id=match_id,
        series_id=_int_value(info.get("seriesId")),
        series_name=str(info.get("seriesName") or ""),
        match_desc=str(info.get("matchDesc") or ""),
        match_format=str(info.get("matchFormat") or ""),
        start=start,
        end=_epoch_ms_to_datetime(info.get("endDate")),
        state=str(info.get("state") or ""),
        status=str(info.get("status") or ""),
        team1=_parse_team(info.get("team1") or {}),
        team2=_parse_team(info.get("team2") or {}),
        venue=_parse_venue(info.get("venueInfo") or {}),
        source_url=f"https://www.cricbuzz.com/live-cricket-scores/{match_id}" if match_id else "",
    )


def _parse_team(data: dict) -> Team:
    return Team(
        team_id=_int_value(data.get("teamId")),
        name=str(data.get("teamName") or ""),
        short_name=str(data.get("teamSName") or ""),
    )


def _parse_venue(data: dict) -> Venue:
    return Venue(
        ground=str(data.get("ground") or ""),
        city=str(data.get("city") or ""),
        timezone=str(data.get("timezone") or ""),
    )


def _epoch_ms_to_datetime(value: object) -> Optional[datetime]:
    if value in (None, ""):
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _int_value(value: object) -> int:
    if value in (None, ""):
        return 0
    return int(value)
