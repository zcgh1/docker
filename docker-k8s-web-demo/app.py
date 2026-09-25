#!/usr/bin/env python3
"""A tiny dependency-free web service for Docker and Kubernetes practice."""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "templates" / "index.html"

APP_NAME = os.getenv("APP_NAME", "web-demo")
APP_VERSION = os.getenv("APP_VERSION", "dev")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "18080"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger(APP_NAME)


class WebDemoHandler(BaseHTTPRequestHandler):
    server_version = "WebDemo/1.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path

        if path == "/":
            self._send_index()
        elif path == "/api/hello":
            self._send_json(
                200,
                {
                    "message": "Hello from the Docker and Kubernetes demo!",
                    "app": APP_NAME,
                    "version": APP_VERSION,
                    "pod": os.getenv("POD_NAME", "local"),
                    "node": os.getenv("NODE_NAME", "local"),
                    "pod_ip": os.getenv("POD_IP", "127.0.0.1"),
                    "time": datetime.now(timezone.utc).isoformat(),
                },
            )
        elif path == "/healthz":
            self._send_text(200, "ok\n")
        elif path == "/readyz":
            self._send_json(200, {"status": "ready"})
        elif path == "/favicon.ico":
            self._send_bytes(204, b"", "image/x-icon")
        else:
            if path.startswith("/api/"):
                self._send_json(404, {"error": "not_found", "path": path})
            else:
                self._send_text(404, "404 Not Found\n")

    def do_HEAD(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self.do_GET()

    def _send_index(self) -> None:
        try:
            body = INDEX_FILE.read_bytes()
        except FileNotFoundError:
            LOGGER.exception("index file is missing: %s", INDEX_FILE)
            self._send_text(500, "index.html is missing\n")
            return

        self._send_bytes(200, body, "text/html; charset=utf-8")

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(
            status,
            body,
            "application/json; charset=utf-8",
            {"Cache-Control": "no-store"},
        )

    def _send_text(self, status: int, text: str) -> None:
        self._send_bytes(status, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        self.end_headers()

        if self.command != "HEAD" and body:
            self.wfile.write(body)

    def log_message(self, message_format: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.client_address[0], message_format % args)


def main() -> None:
    if not INDEX_FILE.is_file():
        raise SystemExit(f"Missing page: {INDEX_FILE}")

    server = ThreadingHTTPServer((HOST, PORT), WebDemoHandler)
    server.daemon_threads = True

    def request_shutdown(signum: int, _frame: object) -> None:
        LOGGER.info("Received signal %s, shutting down", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_shutdown)

    LOGGER.info("%s %s listening on %s:%s", APP_NAME, APP_VERSION, HOST, PORT)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        LOGGER.info("Server stopped")


if __name__ == "__main__":
    main()
