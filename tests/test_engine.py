import requests
import responses

from speedtest import engine
from speedtest.engine import fetch, make_session, run_parallel, run_sequential

URL = "https://example.com/file.bin"


@responses.activate
def test_fetch_ok():
    body = b"a" * 1_000_000
    responses.add(responses.GET, URL, body=body, status=200)
    m = fetch(make_session(), URL, timeout=10.0)
    assert m.error is None
    assert m.status == 200
    assert m.size == len(body)
    assert m.ttfb > 0
    assert m.total >= m.ttfb
    assert m.samples
    assert m.samples[-1].bytes_read == len(body)


@responses.activate
def test_fetch_http_error():
    responses.add(responses.GET, URL, status=404, body=b"not found")
    m = fetch(make_session(), URL, timeout=10.0)
    assert m.error is not None
    assert m.status == 404
    assert m.size == 0
    assert not m.samples


@responses.activate
def test_fetch_connection_error():
    responses.add(responses.GET, URL, body=requests.exceptions.ConnectionError("boom"))
    m = fetch(make_session(), URL, timeout=10.0)
    assert m.error is not None
    assert m.status is None
    assert m.size == 0


@responses.activate
def test_run_sequential():
    body = b"a" * 1000
    for _ in range(12):  # 2 warmup + 10 count
        responses.add(responses.GET, URL, body=body, status=200)
    run = run_sequential(URL, count=10, warmup=2, timeout=10.0)
    assert len(run.measurements) == 10
    assert run.errors == 0
    assert run.total_bytes == 10 * 1000
    assert run.total_time > 0
    assert run.threads == 1


@responses.activate
def test_run_sequential_counts_errors():
    for _ in range(2):  # 1 warmup + 1 count
        responses.add(responses.GET, URL, status=500, body=b"err")
    run = run_sequential(URL, count=1, warmup=1, timeout=10.0)
    assert run.errors == 1
    assert run.total_bytes == 0


@responses.activate
def test_run_parallel_all_ok():
    body = b"a" * 1000
    for _ in range(14):  # max(warmup=1, threads=4)=4 warmup + 10 count
        responses.add(responses.GET, URL, body=body, status=200)
    run = run_parallel(URL, count=10, threads=4, warmup=1, timeout=10.0)
    assert len(run.measurements) == 10
    assert run.errors == 0
    assert run.threads == 4
    assert run.total_bytes == 10 * 1000
    assert run.wall_clock > 0


@responses.activate
def test_run_parallel_counts_errors():
    for _ in range(12):  # max(warmup=1, threads=2)=2 warmup + 10 count
        responses.add(responses.GET, URL, status=500, body=b"err")
    run = run_parallel(URL, count=10, threads=2, warmup=1, timeout=10.0)
    assert run.errors == 10
    assert run.total_bytes == 0


def test_run_parallel_interrupted(monkeypatch):
    def boom(url, timeout):
        raise KeyboardInterrupt

    monkeypatch.setattr(engine, "_fetch_threaded", boom)
    run = engine.run_parallel(URL, count=3, threads=2, warmup=0, timeout=10.0)
    assert run.interrupted is True
    assert run.measurements == ()
