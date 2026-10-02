"""Точка входа CLI: argparse, валидация, коды возврата."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from speedtest import curve, engine, verdict
from speedtest.models import MB, Measurement, RunResult, speed_mb_s
from speedtest.phases import measure as measure_phases
from speedtest.render import render_phases, render_summary, render_verdict


def build_parser() -> argparse.ArgumentParser:
    """Собирает парсер аргументов CLI."""
    parser = argparse.ArgumentParser(
        prog="speedtest",
        description="Замер скорости скачивания по HTTP",
    )
    parser.add_argument("url", help="адрес файла для скачивания")
    parser.add_argument(
        "-n", "--count", type=int, default=10, help="число запросов (по умолчанию 10)"
    )
    parser.add_argument(
        "-w",
        "--warmup",
        type=int,
        default=1,
        help="прогревочные запросы (по умолчанию 1)",
    )
    parser.add_argument("-t", "--timeout", type=float, default=30.0, help="таймаут, с")
    parser.add_argument(
        "-j", "--threads", type=int, default=1, help="число параллельных потоков"
    )
    parser.add_argument(
        "--json", dest="json_path", metavar="PATH", help="экспорт результата в JSON"
    )
    parser.add_argument(
        "--phases", action="store_true", help="показать фазы соединения"
    )
    parser.add_argument(
        "--probe-threads",
        type=int,
        metavar="N",
        help="сравнить 1 поток против N потоков и вывести вердикт",
    )
    return parser


def _validate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Проверяет аргументы; при нарушении завершает работу с ошибкой."""
    if not args.url.startswith(("http://", "https://")):
        parser.error("URL должен начинаться с http:// или https://")
    if args.count < 1:
        parser.error("--count должен быть >= 1")
    if args.warmup < 0:
        parser.error("--warmup не может быть отрицательным")
    if args.threads < 1:
        parser.error("--threads должен быть >= 1")
    if args.probe_threads is not None and args.json_path:
        parser.error("--json несовместим с --probe-threads")
    if args.probe_threads is not None and args.probe_threads < 2:
        parser.error("--probe-threads должен быть >= 2")


def write_json(path: str, run: RunResult, args: argparse.Namespace) -> bool:
    """Записывает результат прогона в JSON-файл.

    Возвращает True при успехе, False при ошибке записи.
    """
    data = {
        "meta": {
            "url": args.url,
            "count": args.count,
            "warmup": args.warmup,
            "threads": args.threads,
            "timeout": args.timeout,
            "timestamp_utc": datetime.now(UTC).isoformat(),
        },
        "run": run.to_dict(),
    }
    try:
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        print(f"Не удалось записать JSON в {path}: {exc}", file=sys.stderr)
        return False
    return True


def _report(i: int, m: Measurement) -> None:
    """Печатает строку прогресса сразу после замера."""
    if m.error is not None:
        print(f"#{i:>2}: ошибка: {m.error}", flush=True)
        return
    speed = speed_mb_s(m.size, m.total)
    spark = curve.analyze(m.samples, spark_width=12).sparkline
    print(
        f"#{i:>2}: {m.total:.3f} с | {m.size / MB:.2f} МБ | "
        f"{speed:.2f} МБ/с | TTFB {m.ttfb * 1000:.0f} мс | {spark}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    """Точка входа: парсит аргументы, запускает замер и выводит результат."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate(args, parser)

    if args.probe_threads is not None:
        v = verdict.probe(
            args.url, args.probe_threads, args.count, args.warmup, args.timeout
        )
        render_verdict(v)
        return 0

    if args.phases:
        phases = measure_phases(args.url, args.timeout)
    else:
        phases = None

    if args.threads > 1:
        run = engine.run_parallel(
            args.url, args.count, args.threads, args.warmup, args.timeout, _report
        )
    else:
        run = engine.run_sequential(
            args.url, args.count, args.warmup, args.timeout, _report
        )

    render_summary(run)
    if phases is not None:
        render_phases(phases)

    if args.json_path and not write_json(args.json_path, run, args):
        return 2

    if run.interrupted:
        return 130
    if not run.succeeded:
        return 1
    return 0
