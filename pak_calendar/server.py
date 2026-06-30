from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlparse

from .calendar import generate_ics
from .cricbuzz import DEFAULT_SOURCE_URL, fetch_matches
from .filters import filter_pakistan_mens_matches
from .models import CricketMatch


@dataclass(frozen=True)
class CalendarPayload:
    ics: str
    matches: list[CricketMatch]
    generated_at: datetime
    source_url: str

    @property
    def etag(self) -> str:
        digest = hashlib.sha1(self.ics.encode("utf-8")).hexdigest()
        return f'"{digest}"'


class CalendarFeed:
    def __init__(self, source_url: str, cache_seconds: int, include_past: bool = False) -> None:
        self.source_url = source_url
        self.cache_seconds = cache_seconds
        self.include_past = include_past
        self._payload: Optional[CalendarPayload] = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get(self) -> CalendarPayload:
        now_seconds = time.time()
        with self._lock:
            if self._payload is not None and now_seconds < self._expires_at:
                return self._payload

            generated_at = datetime.now(timezone.utc)
            try:
                raw_matches = fetch_matches(self.source_url)
                matches = filter_pakistan_mens_matches(
                    raw_matches,
                    now=generated_at,
                    include_past=self.include_past,
                )
            except Exception:
                if self._payload is not None:
                    self._expires_at = now_seconds + min(600, self.cache_seconds)
                    return self._payload
                raise
            payload = CalendarPayload(
                ics=generate_ics(matches, generated_at=generated_at),
                matches=matches,
                generated_at=generated_at,
                source_url=self.source_url,
            )
            self._payload = payload
            self._expires_at = now_seconds + self.cache_seconds
            return payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Serve Pakistan men's cricket calendar feed.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", default=8765, type=int, help="Bind port")
    parser.add_argument(
        "--source-url",
        default=os.environ.get("PAK_CALENDAR_SOURCE_URL", DEFAULT_SOURCE_URL),
        help="Cricbuzz schedule URL",
    )
    parser.add_argument(
        "--cache-seconds",
        default=int(os.environ.get("PAK_CALENDAR_CACHE_SECONDS", "21600")),
        type=int,
        help="Feed cache TTL",
    )
    parser.add_argument(
        "--include-past",
        action="store_true",
        default=os.environ.get("PAK_CALENDAR_INCLUDE_PAST") == "1",
        help="Include past matches",
    )
    args = parser.parse_args(argv)

    feed = CalendarFeed(
        source_url=args.source_url,
        cache_seconds=args.cache_seconds,
        include_past=args.include_past,
    )
    handler = _make_handler(feed)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Pakistan men's cricket calendar running at http://{args.host}:{args.port}/pakistan-men.ics")
    server.serve_forever()
    return 0


def _make_handler(feed: CalendarFeed):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PakistanMensCricketCalendar/0.1"

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._send_text(_index_text(self.headers.get("Host", "localhost:8765")), "text/plain; charset=utf-8")
                return
            if path == "/health":
                self._send_text("ok\n", "text/plain; charset=utf-8")
                return
            if path == "/pakistan-men.ics":
                self._send_calendar()
                return
            if path == "/matches.json":
                self._send_matches_json()
                return
            self.send_error(404, "Not found")

        def _send_calendar(self) -> None:
            try:
                payload = feed.get()
            except Exception as exc:  # pragma: no cover - exercised manually against network failures.
                self.send_error(502, f"Could not refresh calendar: {exc}")
                return

            if self.headers.get("If-None-Match") == payload.etag:
                self.send_response(304)
                self.send_header("ETag", payload.etag)
                self.end_headers()
                return

            body = payload.ics.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'inline; filename="pakistan-men.ics"')
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("ETag", payload.etag)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_matches_json(self) -> None:
            try:
                payload = feed.get()
            except Exception as exc:  # pragma: no cover - exercised manually against network failures.
                self.send_error(502, f"Could not refresh matches: {exc}")
                return
            body = json.dumps(
                {
                    "source_url": payload.source_url,
                    "generated_at": payload.generated_at.isoformat(),
                    "count": len(payload.matches),
                    "matches": [match.to_dict() for match in payload.matches],
                },
                indent=2,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, text: str, content_type: str) -> None:
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"{self.address_string()} - {fmt % args}")

    return Handler


def _index_text(host: str) -> str:
    return (
        "Pakistan men's cricket calendar\n\n"
        f"Apple Calendar subscription URL: http://{host}/pakistan-men.ics\n"
        f"Debug JSON: http://{host}/matches.json\n"
        "Health check: /health\n\n"
        "Apple Calendar: File -> New Calendar Subscription... -> paste the subscription URL.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
