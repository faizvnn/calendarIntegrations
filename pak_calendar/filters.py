from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from .models import CricketMatch

PAKISTAN_MENS_TEAM_ID = 3
ALLOWED_FORMATS = {"TEST", "ODI", "T20", "T20I"}

MATCH_EXCLUSION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bwarm[- ]?up\b",
        r"\bpractice\b",
        r"\btour match\b",
        r"\bintra[- ]?squad\b",
    ]
]

TEAM_EXCLUSION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bwom[ae]n'?s?\b",
        r"\bfemale\b",
        r"\bunder[- ]?\d+\b",
        r"\bu[- ]?\d+\b",
        r"\b[aA]\b",
        r"\bselect\b",
        r"\bxi\b",
        r"\bboard\b",
        r"\bpresident'?s?\b",
        r"\binvitational\b",
        r"\bacademy\b",
        r"\bemerging\b",
        r"\bdevelopment\b",
        r"\blions\b",
    ]
]


def filter_pakistan_mens_matches(
    matches: Iterable[CricketMatch],
    now: Optional[datetime] = None,
    include_past: bool = False,
) -> List[CricketMatch]:
    comparison_time = _as_utc(now or datetime.now(timezone.utc))
    filtered = [
        match
        for match in matches
        if is_pakistan_mens_international(match)
        and (include_past or match.calendar_end() >= comparison_time - timedelta(hours=12))
    ]
    return sorted(filtered, key=lambda match: (match.start, match.match_id))


def is_pakistan_mens_international(match: CricketMatch) -> bool:
    if match.match_format.upper() not in ALLOWED_FORMATS:
        return False

    if PAKISTAN_MENS_TEAM_ID not in {match.team1.team_id, match.team2.team_id}:
        return False

    if _has_match_exclusion(match.series_name) or _has_match_exclusion(match.match_desc):
        return False

    opponent = match.opponent(PAKISTAN_MENS_TEAM_ID)
    if opponent is None:
        return False

    return not _has_team_exclusion(opponent.name) and not _has_team_exclusion(match.team1.name) and not _has_team_exclusion(match.team2.name)


def _has_match_exclusion(value: str) -> bool:
    return any(pattern.search(value or "") for pattern in MATCH_EXCLUSION_PATTERNS)


def _has_team_exclusion(value: str) -> bool:
    return any(pattern.search(value or "") for pattern in TEAM_EXCLUSION_PATTERNS)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
