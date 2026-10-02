import pytest

from speedtest.models import (
    MB,
    MIN_P95_N,
    coefficient_of_variation,
    jitter,
    median_absolute_deviation,
    p95,
    percentile,
    speed_mb_s,
    stability_label,
)


def test_mb_is_decimal():
    assert MB == 1_000_000


class TestPercentile:
    def test_sorted_even(self):
        assert percentile([1, 2, 3, 4], 0.5) == pytest.approx(2.5)

    def test_single_value(self):
        assert percentile([5.0], 0.95) == pytest.approx(5.0)

    def test_p95_known(self):
        data = list(range(1, 21))
        assert percentile(data, 0.95) == pytest.approx(19.05)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            percentile([], 0.5)


class TestP95:
    def test_returns_none_below_threshold(self):
        assert p95([1.0, 2.0, 3.0]) is None

    def test_returns_value_at_threshold(self):
        data = [float(i) for i in range(1, MIN_P95_N + 1)]
        assert p95(data) == pytest.approx(percentile(data, 0.95))

    def test_empty(self):
        assert p95([]) is None


class TestJitter:
    def test_constant_series(self):
        assert jitter([1.0, 1.0, 1.0]) == 0.0

    def test_two_values(self):
        assert jitter([1.0, 3.0]) == 2.0

    def test_single_value(self):
        assert jitter([5.0]) == 0.0

    def test_empty(self):
        assert jitter([]) == 0.0

    def test_mean_absolute_adjacent(self):
        assert jitter([1.0, 4.0, 2.0]) == pytest.approx(2.5)


class TestCoefficientOfVariation:
    def test_zero_variance(self):
        assert coefficient_of_variation([5.0, 5.0, 5.0]) == 0.0

    def test_known(self):
        # mean=15, sample stdev=sqrt(50)≈7.071 → cv≈47.14%
        assert coefficient_of_variation([10.0, 20.0]) == pytest.approx(
            47.1405, rel=1e-3
        )

    def test_single_value(self):
        assert coefficient_of_variation([5.0]) == 0.0

    def test_empty(self):
        assert coefficient_of_variation([]) == 0.0


class TestMedianAbsoluteDeviation:
    def test_symmetric(self):
        # median=3, |x-3|=[2,1,0,1,2], median=1
        assert median_absolute_deviation([1.0, 2.0, 3.0, 4.0, 5.0]) == 1.0

    def test_single_value(self):
        assert median_absolute_deviation([7.0]) == 0.0


class TestStabilityLabel:
    def test_stable(self):
        assert stability_label(5.0) == "стабильно"

    def test_fluctuating(self):
        assert stability_label(15.0) == "плавает"

    def test_unstable(self):
        assert stability_label(30.0) == "нестабильно"

    def test_boundaries(self):
        assert stability_label(10.0) == "плавает"
        assert stability_label(25.0) == "плавает"


class TestSpeedMbS:
    def test_one_megabyte_per_second(self):
        assert speed_mb_s(1_000_000, 1.0) == pytest.approx(1.0)

    def test_zero_bytes(self):
        assert speed_mb_s(0, 1.0) == 0.0

    def test_zero_seconds(self):
        assert speed_mb_s(1_000_000, 0.0) == 0.0
