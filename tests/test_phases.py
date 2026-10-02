import socket

from speedtest.phases import _build_request, _default_port, measure


def test_default_port():
    assert _default_port("https") == 443
    assert _default_port("http") == 80


def test_build_request():
    req = _build_request("example.com", "/file")
    assert b"GET /file HTTP/1.1" in req
    assert b"Host: example.com" in req


def test_measure_no_host():
    p = measure("https://")
    assert p.error == "нет хоста в URL"


def test_measure_dns_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("dns fail")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    p = measure("https://example.com/file")
    assert p.error == "dns fail"
    assert p.dns == 0.0
