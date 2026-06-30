import json
import unittest
from datetime import datetime, timezone

from pak_calendar.calendar import generate_ics
from pak_calendar.cricbuzz import extract_matches_from_html
from pak_calendar.filters import filter_pakistan_mens_matches, is_pakistan_mens_international


def _html_with_matches(*match_infos):
    matches = [{"matchInfo": match_info} for match_info in match_infos]
    payload = '2c:["$","div",null,{"data":{"teamMatchesData":[{"matchDetailsMap":{"match":'
    payload += json.dumps(matches, separators=(",", ":"))
    payload += '}}]}}]'
    return f"<html><body><script>self.__next_f.push([1,{json.dumps(payload)}])</script></body></html>"


def _match_info(**overrides):
    base = {
        "matchId": 152496,
        "seriesId": 11968,
        "seriesName": "Pakistan tour of West Indies, 2026",
        "matchDesc": "1st Test",
        "matchFormat": "TEST",
        "startDate": "1784988000000",
        "endDate": "1785358800000",
        "state": "Upcoming",
        "status": "Match starts at Jul 25, 14:00 GMT",
        "team1": {"teamId": 10, "teamName": "West Indies", "teamSName": "WI"},
        "team2": {"teamId": 3, "teamName": "Pakistan", "teamSName": "PAK"},
        "venueInfo": {
            "ground": "Brian Lara Stadium",
            "city": "Tarouba, Trinidad",
            "timezone": "-04:00",
        },
    }
    base.update(overrides)
    return base


class CalendarTests(unittest.TestCase):
    def test_extracts_cricbuzz_next_fixture_data(self):
        html = _html_with_matches(_match_info())

        matches = extract_matches_from_html(html)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_id, 152496)
        self.assertEqual(matches[0].team2.team_id, 3)
        self.assertEqual(matches[0].venue.city, "Tarouba, Trinidad")

    def test_filters_only_senior_mens_official_formats(self):
        official = _match_info(matchId=1)
        warmup = _match_info(
            matchId=2,
            matchDesc="4 -Day Warm-up match",
            team1={"teamId": 2277, "teamName": "West Indies Select XI", "teamSName": "WISXI"},
        )
        pakistan_a = _match_info(
            matchId=3,
            team2={"teamId": 3, "teamName": "Pakistan", "teamSName": "PAK"},
            team1={"teamId": 999, "teamName": "Australia A", "teamSName": "AUSA"},
        )
        wrong_format = _match_info(matchId=4, matchFormat="FC")
        html = _html_with_matches(official, warmup, pakistan_a, wrong_format)

        matches = extract_matches_from_html(html)
        filtered = filter_pakistan_mens_matches(
            matches,
            now=datetime(2026, 6, 30, tzinfo=timezone.utc),
        )

        self.assertEqual([match.match_id for match in filtered], [1])
        self.assertTrue(is_pakistan_mens_international(filtered[0]))

    def test_generates_apple_calendar_ics(self):
        html = _html_with_matches(_match_info())
        matches = filter_pakistan_mens_matches(
            extract_matches_from_html(html),
            now=datetime(2026, 6, 30, tzinfo=timezone.utc),
        )

        ics = generate_ics(matches, generated_at=datetime(2026, 6, 30, tzinfo=timezone.utc))

        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn("SUMMARY:West Indies vs Pakistan - 1st Test", ics)
        self.assertIn("DTSTART:20260725T140000Z", ics)
        self.assertIn("LOCATION:Brian Lara Stadium\\, Tarouba\\, Trinidad", ics)


if __name__ == "__main__":
    unittest.main()
