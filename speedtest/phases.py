"""Фазы установления соединения: DNS, TCP, TLS, TTFB.

Измеряет отдельное пробное соединение через stdlib (socket/ssl), а не то,
что происходит внутри requests.Session.
"""

from __future__ import annotations

import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Phases:
    """Времена фаз установления соединения (секунды)."""

    host: str
    port: int
    dns: float
    tcp: float
    tls: float
    ttfb: float
    error: str | None


def _default_port(scheme: str) -> int:
    """Порт по умолчанию для схемы."""
    return 443 if scheme == "https" else 80


def _build_request(host: str, path: str) -> bytes:
    """Минимальный GET-запрос для замера TTFB."""
    return (
        f"GET {path or '/'} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    ).encode()


def measure(url: str, timeout: float = 10.0) -> Phases:
    """Измеряет DNS → TCP connect → TLS handshake → TTFB."""
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or _default_port(parsed.scheme)
    if not host:
        return Phases("", 0, 0.0, 0.0, 0.0, 0.0, "нет хоста в URL")

    dns = tcp = tls = ttfb = 0.0
    sock: socket.socket | None = None
    try:
        t0 = time.perf_counter()
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        dns = time.perf_counter() - t0

        t0 = time.perf_counter()
        sock = socket.create_connection((host, port), timeout=timeout)
        tcp = time.perf_counter() - t0

        if parsed.scheme == "https":
            t0 = time.perf_counter()
            context = ssl.create_default_context()
            sock = context.wrap_socket(sock, server_hostname=host)
            tls = time.perf_counter() - t0

        request = _build_request(host, parsed.path or "/")
        t0 = time.perf_counter()
        sock.sendall(request)
        sock.recv(1)
        ttfb = time.perf_counter() - t0

        return Phases(host, port, dns, tcp, tls, ttfb, None)
    except (OSError, ssl.SSLError) as exc:
        return Phases(host, port, dns, tcp, tls, ttfb, str(exc))
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass  # закрытие сокета не должно маскировать результат замера
