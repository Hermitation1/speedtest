"""Кривая скорости внутри запроса: окна, sparkline, выход на плато.

Не импортирует rich — только чистые расчёты и текстовая спарклайн.
"""

from __future__ import annotations

import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from speedtest.models import MB, Sample

_UNICODE_BLOCKS = "▁▂▃▄▅▆▇█"
_ASCII_BLOCKS = "_-="

# Фиксируется при импорте — до принудительного reconfigure в cli.main().
_STDOUT_UTF8 = "utf" in (sys.stdout.encoding or "").lower()


def _spark_blocks() -> str:
    """Набор символов спарклайна: unicode-блоки на UTF-8, иначе ASCII."""
    return _UNICODE_BLOCKS if _STDOUT_UTF8 else _ASCII_BLOCKS


DEFAULT_WINDOW = 0.25
DEFAULT_SPARK_WIDTH = 20
PLATEAU_THRESHOLD = 0.9


@dataclass(frozen=True)
class CurveStats:
    """Сводка по кривой скорости одного запроса."""

    windows: tuple[tuple[float, float], ...]
    sparkline: str
    peak_mb_s: float
    steady_mb_s: float
    plateau_time: float | None


def _bytes_at(samples: Sequence[Sample], t: float) -> float:
    """Накопленные байты к моменту t (линейная интерполяция)."""
    if t <= 0:
        return 0.0
    last = samples[-1]
    if t >= last.elapsed:
        return float(last.bytes_read)
    prev = samples[0]
    for s in samples:
        if s.elapsed >= t:
            if s.elapsed == prev.elapsed:
                return float(s.bytes_read)
            frac = (t - prev.elapsed) / (s.elapsed - prev.elapsed)
            return prev.bytes_read + frac * (s.bytes_read - prev.bytes_read)
        prev = s
    return float(last.bytes_read)


def speed_windows(
    samples: Sequence[Sample], window: float = DEFAULT_WINDOW
) -> list[tuple[float, float]]:
    """Скорость по окнам времени. Возвращает (середина окна, МБ/с)."""
    if not samples or samples[-1].elapsed <= 0:
        return []
    total = samples[-1].elapsed
    result: list[tuple[float, float]] = []
    t = 0.0
    while t < total:
        t_end = min(t + window, total)
        duration = t_end - t
        speed = (_bytes_at(samples, t_end) - _bytes_at(samples, t)) / MB / duration
        result.append(((t + t_end) / 2, speed))
        t = t_end
    return result


def _downsample(values: Sequence[float], width: int) -> list[float]:
    """Сжимает значения до width бакетов, усредняя внутри каждого."""
    result: list[float] = []
    bucket = len(values) / width
    for i in range(width):
        lo = int(i * bucket)
        hi = max(int((i + 1) * bucket), lo + 1)
        chunk = values[lo:hi]
        result.append(sum(chunk) / len(chunk))
    return result


def sparkline(values: Sequence[float], width: int = DEFAULT_SPARK_WIDTH) -> str:
    """Текстовая спарклайн скорости."""
    if not values:
        return ""
    if len(values) > width:
        values = _downsample(values, width)
    blocks = _spark_blocks()
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return blocks[len(blocks) // 2] * len(values)
    return "".join(
        blocks[round((v - vmin) / (vmax - vmin) * (len(blocks) - 1))] for v in values
    )


def plateau_time(
    windows: Sequence[tuple[float, float]], threshold: float = PLATEAU_THRESHOLD
) -> float | None:
    """Время первого окна, где скорость >= threshold * медианы второй половины."""
    if not windows:
        return None
    speeds = [s for _, s in windows]
    second_half = speeds[len(speeds) // 2 :]
    if not second_half:
        return None
    target = statistics.median(second_half) * threshold
    for t, s in windows:
        if s >= target:
            return t
    return None


def analyze(
    samples: Sequence[Sample],
    window: float = DEFAULT_WINDOW,
    spark_width: int = DEFAULT_SPARK_WIDTH,
) -> CurveStats:
    """Полный разбор кривой одного запроса."""
    windows = speed_windows(samples, window)
    speeds = [s for _, s in windows]
    if not speeds:
        return CurveStats((), "", 0.0, 0.0, None)
    steady = statistics.median(speeds[len(speeds) // 2 :])
    return CurveStats(
        tuple(windows),
        sparkline(speeds, spark_width),
        max(speeds),
        steady,
        plateau_time(windows),
    )
