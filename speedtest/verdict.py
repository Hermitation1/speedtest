"""Сравнение скорости 1 поток против N потоков и вердикт."""

from __future__ import annotations

from dataclasses import dataclass

from speedtest import engine
from speedtest.models import speed_mb_s

RATIO_THRESHOLD = 1.5
PROBE_COUNT = 5


@dataclass(frozen=True)
class Verdict:
    """Результат сравнения скорости 1 поток против N потоков."""

    single_mb_s: float
    multi_mb_s: float
    ratio: float
    threads: int
    message: str


def compare_message(ratio: float, threshold: float = RATIO_THRESHOLD) -> str:
    """Формулирует вердикт по соотношению скоростей."""
    if ratio > threshold:
        return f"вероятно ограничение скорости на одно соединение (×{ratio:.2f})"
    return "канал насыщен одним потоком"


def probe(
    url: str,
    threads: int,
    count: int = PROBE_COUNT,
    warmup: int = 1,
    timeout: float = 30.0,
) -> Verdict:
    """Короткий прогон 1 поток против N потоков и вердикт."""
    single = engine.run_sequential(url, count, warmup, timeout)
    multi = engine.run_parallel(url, count, threads, warmup, timeout)
    single_speed = speed_mb_s(single.total_bytes, single.wall_clock)
    multi_speed = speed_mb_s(multi.total_bytes, multi.wall_clock)
    ratio = multi_speed / single_speed if single_speed > 0 else 0.0
    return Verdict(single_speed, multi_speed, ratio, threads, compare_message(ratio))
