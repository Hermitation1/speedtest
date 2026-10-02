"""Модели данных и чистые расчёты для speedtest.

Модуль не импортирует rich и не делает ввод-вывод — только структуры
и расчёты, которые легко тестировать без сети.
"""

from __future__ import annotations

import itertools
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

MB = 1_000_000
MIN_P95_N = 20
P95_FRACTION = 0.95
STABLE_CV = 10.0
UNSTABLE_CV = 25.0


def percentile(values: Sequence[float], p: float) -> float:
    """Перцентиль с линейной интерполяцией (как в numpy)."""
    sorted_values = sorted(values)
    if not sorted_values:
        raise ValueError("percentile() of empty sequence")
    k = (len(sorted_values) - 1) * p
    lower = int(k)
    upper = lower + 1 if lower + 1 < len(sorted_values) else lower
    return sorted_values[lower] + (k - lower) * (
        sorted_values[upper] - sorted_values[lower]
    )


def p95(values: Sequence[float]) -> float | None:
    """95-й перцентиль; None, если точек меньше MIN_P95_N (не подменяем максимумом)."""
    if len(values) < MIN_P95_N:
        return None
    return percentile(values, P95_FRACTION)


def jitter(values: Sequence[float]) -> float:
    """Среднее абсолютное отличие между соседними замерами."""
    if len(values) < 2:
        return 0.0
    diffs = [abs(b - a) for a, b in itertools.pairwise(values)]
    return sum(diffs) / len(diffs)


def coefficient_of_variation(values: Sequence[float]) -> float:
    """Коэффициент вариации в процентах: stdev / mean * 100."""
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    return statistics.stdev(values) / mean * 100.0


def median_absolute_deviation(values: Sequence[float]) -> float:
    """Медианное абсолютное отклонение."""
    med = statistics.median(values)
    return statistics.median([abs(v - med) for v in values])


def stability_label(cv: float) -> str:
    """Оценка стабильности по коэффициенту вариации (в процентах)."""
    if cv < STABLE_CV:
        return "стабильно"
    if cv <= UNSTABLE_CV:
        return "плавает"
    return "нестабильно"


def speed_mb_s(total_bytes: int, seconds: float) -> float:
    """Скорость в МБ/с (десятичный мегабайт)."""
    if seconds <= 0:
        return 0.0
    return total_bytes / MB / seconds


class Sample(NamedTuple):
    """Точка кривой скорости: время от начала запроса и накопленные байты."""

    elapsed: float
    bytes_read: int


@dataclass(frozen=True)
class Measurement:
    """Результат одного запроса."""

    ttfb: float
    total: float
    size: int
    status: int | None
    error: str | None
    samples: tuple[Sample, ...]

    def to_dict(self) -> dict:
        """Сериализация замера в словарь."""
        return {
            "ttfb": self.ttfb,
            "total": self.total,
            "size": self.size,
            "status": self.status,
            "error": self.error,
            "samples": [[s.elapsed, s.bytes_read] for s in self.samples],
        }


@dataclass(frozen=True)
class RunResult:
    """Результат прогона (последовательного или параллельного)."""

    measurements: tuple[Measurement, ...]
    wall_clock: float
    interrupted: bool = False
    threads: int = 1

    @property
    def succeeded(self) -> tuple[Measurement, ...]:
        """Успешные замеры (без ошибок)."""
        return tuple(m for m in self.measurements if m.error is None)

    @property
    def errors(self) -> int:
        """Число неудачных запросов."""
        return len(self.measurements) - len(self.succeeded)

    @property
    def total_bytes(self) -> int:
        """Суммарный объём скачанных байт по успешным замерам."""
        return sum(m.size for m in self.succeeded)

    @property
    def total_time(self) -> float:
        """Сумма времён успешных запросов."""
        return sum(m.total for m in self.succeeded)

    def to_dict(self) -> dict:
        """Сериализация прогона в словарь."""
        return {
            "measurements": [m.to_dict() for m in self.measurements],
            "wall_clock": self.wall_clock,
            "interrupted": self.interrupted,
            "threads": self.threads,
            "errors": self.errors,
            "total_bytes": self.total_bytes,
            "total_time": self.total_time,
        }
