import pytest

from speedtest.curve import (
    analyze,
    plateau_time,
    sparkline,
    speed_windows,
)
from speedtest.models import Sample


def _linear_samples() -> list[Sample]:
    """1 МБ/с: 500 КБ за 0.5 с на каждом шаге."""
    return [
        Sample(0.0, 0),
        Sample(0.5, 500_000),
        Sample(1.0, 1_000_000),
        Sample(1.5, 1_500_000),
    ]


class TestSpeedWindows:
    def test_constant_speed(self):
        windows = speed_windows(_linear_samples(), window=0.5)
        assert len(windows) == 3
        for _, speed in windows:
            assert speed == pytest.approx(1.0)

    def test_empty(self):
        assert speed_windows([]) == []

    def test_window_midpoint(self):
        windows = speed_windows(_linear_samples(), window=0.5)
        assert windows[0][0] == pytest.approx(0.25)


class TestSparkline:
    def test_constant_length(self):
        s = sparkline([1.0, 1.0, 1.0])
        assert len(s) == 3
        assert s[0] == s[1] == s[2]

    def test_empty(self):
        assert sparkline([]) == ""

    def test_downsamples(self):
        s = sparkline([float(i) for i in range(100)], width=10)
        assert len(s) == 10


class TestPlateauTime:
    def test_finds_first_plateau_window(self):
        windows = [
            (0.25, 0.5),
            (0.75, 1.0),
            (1.25, 2.0),
            (1.75, 2.0),
            (2.25, 2.0),
        ]
        assert plateau_time(windows) == pytest.approx(1.25)

    def test_empty(self):
        assert plateau_time([]) is None


class TestAnalyze:
    def test_empty(self):
        c = analyze([])
        assert c.windows == ()
        assert c.sparkline == ""
        assert c.peak_mb_s == 0.0
        assert c.steady_mb_s == 0.0
        assert c.plateau_time is None

    def test_linear(self):
        c = analyze(_linear_samples(), window=0.5)
        assert c.peak_mb_s == pytest.approx(1.0)
        assert c.steady_mb_s == pytest.approx(1.0)
