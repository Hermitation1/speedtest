"""Вывод через rich. Без сетевой логики — только печать."""

from __future__ import annotations

import statistics

from rich.console import Console
from rich.table import Table

from speedtest import curve
from speedtest.models import (
    MB,
    RunResult,
    coefficient_of_variation,
    median_absolute_deviation,
    speed_mb_s,
    stability_label,
)
from speedtest.phases import Phases
from speedtest.verdict import Verdict

console = Console()

TABLE_SPARK_WIDTH = 12


def _format_mb(size: int) -> str:
    """Форматирует байты в строку МБ с двумя знаками."""
    return f"{size / MB:.2f}"


def render(run: RunResult) -> None:
    """Печатает таблицу запросов и сводку."""
    table = Table(title="Запросы")
    table.add_column("#", justify="right")
    table.add_column("время, с", justify="right")
    table.add_column("МБ", justify="right")
    table.add_column("МБ/с", justify="right")
    table.add_column("TTFB, мс", justify="right")
    table.add_column("кривая")
    table.add_column("статус", justify="right")

    for i, m in enumerate(run.measurements, start=1):
        if m.error is not None:
            table.add_row(str(i), "—", "—", "—", "—", "—", "ошибка")
            continue
        speed = speed_mb_s(m.size, m.total)
        spark = curve.analyze(m.samples, spark_width=TABLE_SPARK_WIDTH).sparkline
        table.add_row(
            str(i),
            f"{m.total:.3f}",
            _format_mb(m.size),
            f"{speed:.2f}",
            f"{m.ttfb * 1000:.0f}",
            spark,
            str(m.status),
        )

    console.print(table)
    _print_summary(run)


def render_summary(run: RunResult) -> None:
    """Печатает только итоговую сводку (без таблицы запросов)."""
    _print_summary(run)


def _print_summary(run: RunResult) -> None:
    """Печатает итоговую сводку прогона."""
    if not run.succeeded:
        console.print("[red]Нет ни одного успешного запроса.[/red]")
        return

    times = [m.total for m in run.succeeded]
    ttfbs = [m.ttfb for m in run.succeeded]
    speeds = [speed_mb_s(m.size, m.total) for m in run.succeeded]
    per_stream = speed_mb_s(run.total_bytes, run.total_time)
    aggregated = speed_mb_s(run.total_bytes, run.wall_clock)
    last_curve = curve.analyze(run.succeeded[-1].samples)
    cv = coefficient_of_variation(speeds)
    mad = median_absolute_deviation(speeds)

    console.print()
    console.print("[bold]Итог[/bold]")
    console.print(
        f"Успешно: {len(run.succeeded)} из {len(run.measurements)} "
        f"(ошибок: {run.errors})"
    )
    console.print(
        f"Среднее время: {statistics.mean(times):.3f} с "
        f"(min {min(times):.3f}, max {max(times):.3f})"
    )
    console.print(f"Среднее TTFB: {statistics.mean(ttfbs) * 1000:.0f} мс")
    console.print(f"Скачано всего: {_format_mb(run.total_bytes)} МБ")
    if run.threads > 1:
        console.print(
            f"Скорость суммарная: {aggregated:.2f} МБ/с ({aggregated * 8:.1f} Мбит/с)"
        )
        console.print(f"Скорость на поток: {per_stream:.2f} МБ/с")
    else:
        console.print(f"Скорость: {per_stream:.2f} МБ/с ({per_stream * 8:.1f} Мбит/с)")
    console.print(
        f"Пиковая скорость: {last_curve.peak_mb_s:.2f} МБ/с, "
        f"установившаяся: {last_curve.steady_mb_s:.2f} МБ/с"
    )
    console.print(
        f"Стабильность: {stability_label(cv)} (CV {cv:.1f}%, MAD {mad:.2f} МБ/с)"
    )


def render_phases(p: Phases) -> None:
    """Печатает фазы установления соединения."""
    console.print()
    console.print("[bold]Фазы соединения (отдельное пробное подключение)[/bold]")
    if p.error is not None:
        console.print(f"[red]Ошибка: {p.error}[/red]")
        return
    table = Table()
    table.add_column("этап")
    table.add_column("время, мс", justify="right")
    table.add_row("DNS", f"{p.dns * 1000:.1f}")
    table.add_row("TCP connect", f"{p.tcp * 1000:.1f}")
    table.add_row("TLS handshake", f"{p.tls * 1000:.1f}")
    table.add_row("TTFB", f"{p.ttfb * 1000:.1f}")
    console.print(table)


def render_verdict(v: Verdict) -> None:
    """Печатает сравнение 1 поток против N потоков."""
    console.print()
    console.print("[bold]Сравнение потоков[/bold]")
    console.print(f"1 поток: {v.single_mb_s:.2f} МБ/с")
    console.print(f"{v.threads} потоков: {v.multi_mb_s:.2f} МБ/с")
    console.print(f"Вердикт: {v.message}")
