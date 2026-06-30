from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass(frozen=True)
class Team:
    team_id: int
    name: str
    short_name: str = ""

    def display_name(self) -> str:
        return clean_team_name(self.name)


@dataclass(frozen=True)
class Venue:
    ground: str = ""
    city: str = ""
    timezone: str = ""

    def display_name(self) -> str:
        parts = [part for part in [self.ground, self.city] if part]
        return ", ".join(parts)


@dataclass(frozen=True)
class CricketMatch:
    match_id: int
    series_id: int
    series_name: str
    match_desc: str
    match_format: str
    start: datetime
    end: Optional[datetime]
    state: str
    status: str
    team1: Team
    team2: Team
    venue: Venue
    source_url: str = ""
    source: str = "Cricbuzz"

    def summary(self) -> str:
        teams = f"{self.team1.display_name()} vs {self.team2.display_name()}"
        if self.match_desc:
            return f"{teams} - {self.match_desc}"
        return f"{teams} - {format_label(self.match_format)}"

    def opponent(self, team_id: int) -> Optional[Team]:
        if self.team1.team_id == team_id:
            return self.team2
        if self.team2.team_id == team_id:
            return self.team1
        return None

    def calendar_end(self) -> datetime:
        start = as_utc(self.start)
        if self.end is not None:
            end = as_utc(self.end)
            if end > start + timedelta(minutes=30):
                return end

        match_format = self.match_format.upper()
        if match_format == "ODI":
            return start + timedelta(hours=9)
        if match_format in {"T20", "T20I"}:
            return start + timedelta(hours=4)
        if match_format == "TEST":
            return start + timedelta(days=5, hours=7)
        return start + timedelta(hours=4)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "series_id": self.series_id,
            "series_name": self.series_name,
            "match_desc": self.match_desc,
            "match_format": self.match_format,
            "start": as_utc(self.start).isoformat(),
            "end": self.calendar_end().isoformat(),
            "state": self.state,
            "status": self.status,
            "team1": {
                "id": self.team1.team_id,
                "name": self.team1.name,
                "short_name": self.team1.short_name,
            },
            "team2": {
                "id": self.team2.team_id,
                "name": self.team2.name,
                "short_name": self.team2.short_name,
            },
            "venue": {
                "ground": self.venue.ground,
                "city": self.venue.city,
                "timezone": self.venue.timezone,
            },
            "source_url": self.source_url,
        }


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_label(match_format: str) -> str:
    upper = match_format.upper()
    if upper == "TEST":
        return "Test"
    if upper == "ODI":
        return "ODI"
    if upper in {"T20", "T20I"}:
        return "T20I"
    return match_format


def clean_team_name(value: str) -> str:
    stripped = value.strip()
    if stripped.isupper() and len(stripped) > 3:
        return stripped.title()
    return stripped
