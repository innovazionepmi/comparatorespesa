"""Piccolo server HTTP interno per far lanciare la run a n8n (o a qualsiasi scheduler).

POST /run     header `X-Token: <SPESA_TOKEN>`  -> esegue la pipeline, risponde JSON
GET  /health  -> {"ok": true} (nessun dato)
Una sola run alla volta. Va esposto solo sulla rete Docker interna, mai su Internet.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from spesa.cli import run_all

log = logging.getLogger("spesa.server")
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            log.warning("client disconnesso prima della risposta (la run e' comunque terminata)")

    def do_GET(self) -> None:
        self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        token = os.environ.get("SPESA_TOKEN", "")
        sent = self.headers.get("X-Token", "")
        if self.path != "/run":
            return self._send(404, {"error": "not found"})
        if not token or not hmac.compare_digest(sent, token):
            return self._send(401, {"error": "unauthorized"})
        if not _lock.acquire(blocking=False):
            return self._send(409, {"error": "run gia' in corso"})
        try:
            res = run_all(None, False, "config", "data/prezzi.db", "data/reports")
            self._send(200, res)
        except Exception as e:  # esito leggibile da n8n invece di una connessione chiusa
            log.exception("run fallita")
            self._send(500, {"status": "failed", "error": type(e).__name__, "summary": "run fallita"})
        finally:
            _lock.release()

    def log_message(self, fmt: str, *args) -> None:  # niente indirizzi/dati nei log
        log.info("%s", fmt % args if args else fmt)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if not os.environ.get("SPESA_TOKEN"):
        raise SystemExit("SPESA_TOKEN non impostato")
    port = int(os.environ.get("PORT", "8080"))
    log.info("in ascolto su :%s", port)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
