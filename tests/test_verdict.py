import pytest

from speedtest import engine, verdict
from speedtest.models import Measurement, RunResult
from speedtest.verdict import compare_message

URL = "https://example.com/file.bin"


class TestCompareMessage:
    def test_limited(self):
        assert "ограничение" in compare_message(3.0)

    def test_saturated(self):
        assert "насыщен" in compare_message(1.2)


def test_probe(monkeypatch):
    def fake_sequential(url, count, warmup, timeout):
        m = Measurement(0.1, 1.0, 1_000_000, 200, None, ())
        return RunResult((m,), 1.0)

    def fake_parallel(url, count, threads, warmup, timeout):
        m = Measurement(0.1, 1.0, 3_000_000, 200, None, ())
        return RunResult((m,), 1.0, False, threads)

    monkeypatch.setattr(engine, "run_sequential", fake_sequential)
    monkeypatch.setattr(engine, "run_parallel", fake_parallel)

    v = verdict.probe(URL, threads=4)
    assert v.single_mb_s == pytest.approx(1.0)
    assert v.multi_mb_s == pytest.approx(3.0)
    assert v.ratio == pytest.approx(3.0)
    assert v.threads == 4
