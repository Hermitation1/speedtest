"""Измерения скорости скачивания. Без print — возвращает структуры данных."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.exceptions import HTTPError, RequestException

from speedtest.models import Measurement, RunResult, Sample

CHUNK = 256 * 1024

_HEADERS = {
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
}


def make_session() -> requests.Session:
    """Сессия с отключённым сжатием и кэшем."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    return session


def fetch(session: requests.Session, url: str, timeout: float) -> Measurement:
    """Один запрос. Возвращает ttfb, полное время, байты по сети и кривую скорости."""
    t0 = time.perf_counter()
    try:
        with session.get(url, stream=True, timeout=timeout) as resp:
            ttfb = time.perf_counter() - t0
            resp.raise_for_status()
            samples: list[Sample] = []
            size = 0
            for chunk in resp.raw.stream(CHUNK, decode_content=False):
                size += len(chunk)
                samples.append(Sample(time.perf_counter() - t0, size))
            total = time.perf_counter() - t0
            return Measurement(
                ttfb, total, size, resp.status_code, None, tuple(samples)
            )
    except HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        return Measurement(0.0, time.perf_counter() - t0, 0, status, str(exc), ())
    except RequestException as exc:
        return Measurement(0.0, time.perf_counter() - t0, 0, None, str(exc), ())


OnMeasurement = Callable[[int, Measurement], None]


def run_sequential(
    url: str,
    count: int,
    warmup: int = 1,
    timeout: float = 30.0,
    on_measurement: OnMeasurement | None = None,
) -> RunResult:
    """Последовательный прогон: прогрев + count замеров.

    При Ctrl+C возвращает частичный RunResult с interrupted=True.
    on_measurement вызывается после каждого замера (номер, результат).
    """
    measurements: list[Measurement] = []
    interrupted = False
    try:
        with make_session() as session:
            for _ in range(warmup):
                fetch(session, url, timeout)
            for i in range(count):
                m = fetch(session, url, timeout)
                measurements.append(m)
                if on_measurement is not None:
                    on_measurement(i + 1, m)
    except KeyboardInterrupt:
        interrupted = True
    wall_clock = sum(m.total for m in measurements)
    return RunResult(tuple(measurements), wall_clock, interrupted)


_local = threading.local()


def _thread_session() -> requests.Session:
    """Сессия на поток — рукопожатие не входит в каждый замер."""
    session = getattr(_local, "session", None)
    if session is None:
        session = make_session()
        _local.session = session
    return session


def _fetch_threaded(url: str, timeout: float) -> Measurement:
    """Запрос в потоке, используя thread-local сессию."""
    return fetch(_thread_session(), url, timeout)


def run_parallel(
    url: str,
    count: int,
    threads: int,
    warmup: int = 1,
    timeout: float = 30.0,
    on_measurement: OnMeasurement | None = None,
) -> RunResult:
    """Параллельный прогон через ThreadPoolExecutor.

    Скорость считается по реальному wall-clock времени всего прогона.
    Прогрев идёт через thread-local сессии в тех же потоках, чтобы
    рукопожатие не входило в первый замер каждого потока.
    При Ctrl+C отменяет незапущенные задачи и возвращает частичный результат.
    """
    executor = ThreadPoolExecutor(max_workers=threads)
    measurements: list[Measurement] = []
    interrupted = False
    wall_start = time.perf_counter()
    try:
        if warmup > 0:
            warmup_count = max(warmup, threads)
            for future in as_completed(
                [
                    executor.submit(_fetch_threaded, url, timeout)
                    for _ in range(warmup_count)
                ]
            ):
                future.result()

        wall_start = time.perf_counter()
        futures = [executor.submit(_fetch_threaded, url, timeout) for _ in range(count)]
        for future in as_completed(futures):
            try:
                m = future.result()
            except KeyboardInterrupt:
                interrupted = True
                break
            measurements.append(m)
            if on_measurement is not None:
                on_measurement(len(measurements), m)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    wall_clock = time.perf_counter() - wall_start
    return RunResult(tuple(measurements), wall_clock, interrupted, threads)
