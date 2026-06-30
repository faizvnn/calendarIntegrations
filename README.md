# Pakistan Men's Cricket Calendar

Apple Calendar-compatible `.ics` feed for Pakistan senior men's cricket fixtures only: Tests, ODIs, and T20/T20I matches.

The feed uses the Cricbuzz Pakistan team schedule as its source and filters by the senior men's Pakistan team ID (`3`). It deliberately excludes Pakistan Women, Pakistan A, U19, Select XI, warm-ups, practice games, and other non-international fixtures.

## Quick Start

Run the live calendar server:

```sh
python3 -m pak_calendar.server --port 8765
```

Then subscribe in Apple Calendar:

```text
http://localhost:8765/pakistan-men.ics
```

Apple Calendar path: `File` -> `New Calendar Subscription...` -> paste the URL above.

For a phone or any device away from this Mac, deploy the server or publish the generated `.ics` file to a public URL first.

## Static Export

Generate a standalone calendar file:

```sh
python3 -m pak_calendar.export --output dist/pakistan-men.ics
```

You can host `dist/pakistan-men.ics` anywhere that serves a public URL, then subscribe to that URL from Apple Calendar.

## Local Debug Endpoints

When the server is running:

- `http://localhost:8765/pakistan-men.ics` - Apple Calendar feed
- `http://localhost:8765/matches.json` - filtered fixtures for inspection
- `http://localhost:8765/health` - health check

## Configuration

Environment variables:

- `PAK_CALENDAR_SOURCE_URL` - override the Cricbuzz schedule page
- `PAK_CALENDAR_CACHE_SECONDS` - cache duration for the live server, default `21600`
- `PAK_CALENDAR_INCLUDE_PAST=1` - include past matches

## Tests

```sh
python3 -m unittest
```

## GitHub Automation

This repo includes `.github/workflows/update-calendar.yml`, which can regenerate `dist/pakistan-men.ics` every six hours once the project is on GitHub. After enabling GitHub Pages or another static host, subscribe Apple Calendar to the hosted `.ics` URL.

## Data Source

Default source:

```text
https://www.cricbuzz.com/cricket-team/pakistan/3/schedule
```

The parser reads the fixture data embedded in the page and keeps the calendar subscription stable even when the display markup changes.
