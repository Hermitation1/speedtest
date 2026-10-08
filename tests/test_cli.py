import json

import pytest
import responses

from speedtest.cli import main

URL = "https://example.com/file.bin"


def test_main_invalid_count():
    with pytest.raises(SystemExit):
        main([URL, "-n", "0"])


def test_main_invalid_url():
    with pytest.raises(SystemExit):
        main(["ftp://example.com/file", "-n", "1"])


def test_main_negative_warmup():
    with pytest.raises(SystemExit):
        main([URL, "-w", "-1"])


@responses.activate
def test_main_success(capsys):
    responses.add(responses.GET, URL, body=b"a" * 1000, status=200)
    responses.add(responses.GET, URL, body=b"a" * 1000, status=200)
    assert main([URL, "-n", "1", "-w", "1"]) == 0


@responses.activate
def test_main_all_fail(capsys):
    responses.add(responses.GET, URL, status=500, body=b"err")
    responses.add(responses.GET, URL, status=500, body=b"err")
    assert main([URL, "-n", "1", "-w", "1"]) == 1


@responses.activate
def test_main_json(tmp_path, capsys):
    responses.add(responses.GET, URL, body=b"a" * 1000, status=200)
    responses.add(responses.GET, URL, body=b"a" * 1000, status=200)
    out = tmp_path / "result.json"
    assert main([URL, "-n", "1", "-w", "1", "--json", str(out)]) == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["run"]["total_bytes"] == 1000
    assert data["meta"]["url"] == URL


@responses.activate
def test_main_json_write_error(tmp_path, capsys):
    responses.add(responses.GET, URL, body=b"a" * 1000, status=200)
    responses.add(responses.GET, URL, body=b"a" * 1000, status=200)
    out = tmp_path / "missing" / "result.json"
    assert main([URL, "-n", "1", "-w", "1", "--json", str(out)]) == 2
