"""
Linux OS/perf-oriented workload tracing.

This module starts the kernel-level instrumentation path for the simulator.
It supports two practical sources:

* /proc/<pid>/stat sampling for minor/major fault deltas while a workload runs.
* perf stat wrapping for aggregate kernel counters when Linux perf is available.
* perf mem sampling for hardware load/store memory address samples.

The perf-mem backend is sampled rather than exhaustive, but it is the first
hardware-address-oriented path and maps sampled memory addresses to simulated
pages.
"""
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Optional

import psutil

from ..core.page import Page, PageType


@dataclass
class KernelTraceStats:
    source: str
    minor_faults: int = 0
    major_faults: int = 0
    page_faults: int = 0
    cache_misses: int = 0
    memory_samples: int = 0
    unique_sampled_pages: int = 0
    raw_perf_counters: dict[str, int] = field(default_factory=dict)


@dataclass
class KernelTraceResult:
    events: list[tuple[int, Page]]
    stats: KernelTraceStats


class KernelTraceUnavailable(RuntimeError):
    pass


class ProcFaultTraceRunner:
    def __init__(
        self,
        command: Sequence[str],
        page_allocator: Callable[[PageType], Optional[Page]],
        total_ticks: int,
        sample_interval_sec: float = 0.05,
        accesses_per_fault: int = 1,
        seed: int = 11,
    ):
        self.command = list(command)
        self.page_allocator = page_allocator
        self.total_ticks = total_ticks
        self.sample_interval_sec = sample_interval_sec
        self.accesses_per_fault = accesses_per_fault
        self.random = random.Random(seed)

    def execute_and_trace(self) -> KernelTraceResult:
        _require_linux_proc()
        if not self.command:
            raise ValueError("Kernel trace command cannot be empty")

        process = psutil.Popen(
            self.command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pages: list[Page] = []
        events: list[tuple[int, Page]] = []
        stats = KernelTraceStats(source="procfs")
        previous = _read_proc_faults(process.pid)
        tick = 0

        try:
            while process.poll() is None and tick < self.total_ticks:
                current = _read_proc_faults(process.pid)
                if current is None:
                    break

                minor_delta = max(0, current[0] - previous[0])
                major_delta = max(0, current[1] - previous[1])
                previous = current

                stats.minor_faults += minor_delta
                stats.major_faults += major_delta
                fault_delta = minor_delta + major_delta
                stats.page_faults += fault_delta

                for _ in range(fault_delta):
                    page_type = PageType.FILE if major_delta > 0 and self.random.random() < 0.35 else PageType.ANON
                    page = self.page_allocator(page_type)
                    if page is not None:
                        pages.append(page)

                if pages and fault_delta:
                    access_count = min(len(pages), max(1, fault_delta * self.accesses_per_fault))
                    for page in self.random.sample(pages, access_count):
                        events.append((tick, page))

                tick += 1
                time.sleep(self.sample_interval_sec)
        finally:
            process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"Kernel trace command failed with exit code {process.returncode}")

        return KernelTraceResult(events=events, stats=stats)


class PerfStatTraceRunner:
    PERF_EVENTS = ("page-faults", "minor-faults", "major-faults", "cache-misses")

    def __init__(
        self,
        command: Sequence[str],
        page_allocator: Callable[[PageType], Optional[Page]],
        total_ticks: int,
        seed: int = 13,
    ):
        self.command = list(command)
        self.page_allocator = page_allocator
        self.total_ticks = total_ticks
        self.random = random.Random(seed)

    def execute_and_trace(self) -> KernelTraceResult:
        _require_linux_proc()
        if shutil.which("perf") is None:
            raise KernelTraceUnavailable("Linux perf is not installed or not on PATH")
        if not self.command:
            raise ValueError("Kernel trace command cannot be empty")

        perf_command = [
            "perf",
            "stat",
            "-x",
            ",",
            "-e",
            ",".join(self.PERF_EVENTS),
            *self.command,
        ]
        result = subprocess.run(
            perf_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"perf stat failed with exit code {result.returncode}\n{result.stderr}")

        stats = _parse_perf_stat(result.stderr)
        events = _events_from_aggregate_faults(
            page_faults=stats.page_faults,
            major_faults=stats.major_faults,
            total_ticks=self.total_ticks,
            page_allocator=self.page_allocator,
            rng=self.random,
        )
        return KernelTraceResult(events=events, stats=stats)


class PerfMemTraceRunner:
    def __init__(
        self,
        command: Sequence[str],
        page_allocator: Callable[[PageType], Optional[Page]],
        total_ticks: int,
    ):
        self.command = list(command)
        self.page_allocator = page_allocator
        self.total_ticks = total_ticks

    def execute_and_trace(self) -> KernelTraceResult:
        _require_linux_proc()
        if shutil.which("perf") is None:
            raise KernelTraceUnavailable("Linux perf is not installed or not on PATH")
        if not self.command:
            raise ValueError("Kernel trace command cannot be empty")

        with tempfile.TemporaryDirectory(prefix="tpp-perf-mem-") as trace_dir:
            perf_data = os.path.join(trace_dir, "perf.data")
            record_command = [
                "perf",
                "mem",
                "record",
                "-o",
                perf_data,
                "--",
                *self.command,
            ]
            record = subprocess.run(
                record_command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if record.returncode != 0:
                raise RuntimeError(
                    "perf mem record failed with exit code "
                    f"{record.returncode}\n{record.stderr}"
                )

            script = subprocess.run(
                [
                    "perf",
                    "script",
                    "-i",
                    perf_data,
                    "-F",
                    "time,event,addr",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if script.returncode != 0:
                raise RuntimeError(
                    "perf script failed with exit code "
                    f"{script.returncode}\n{script.stderr}"
                )

        sampled_addresses = _parse_perf_script_addresses(script.stdout)
        events, unique_pages = _events_from_sampled_addresses(
            sampled_addresses=sampled_addresses,
            total_ticks=self.total_ticks,
            page_allocator=self.page_allocator,
        )
        stats = KernelTraceStats(
            source="perf-mem",
            memory_samples=len(sampled_addresses),
            unique_sampled_pages=unique_pages,
        )
        return KernelTraceResult(events=events, stats=stats)


def command_for_python_script(script_path: str) -> list[str]:
    return [sys.executable, script_path]


def run_kernel_traced_workload(
    command: Sequence[str],
    page_allocator: Callable[[PageType], Optional[Page]],
    total_ticks: int,
    tracer: str = "auto",
    sample_interval_sec: float = 0.05,
) -> KernelTraceResult:
    if tracer not in {"auto", "procfs", "perf", "perf-mem"}:
        raise ValueError("tracer must be one of: auto, procfs, perf, perf-mem")

    if tracer == "perf-mem":
        return PerfMemTraceRunner(
            command=command,
            page_allocator=page_allocator,
            total_ticks=total_ticks,
        ).execute_and_trace()

    if tracer in {"auto", "procfs"}:
        try:
            return ProcFaultTraceRunner(
                command=command,
                page_allocator=page_allocator,
                total_ticks=total_ticks,
                sample_interval_sec=sample_interval_sec,
            ).execute_and_trace()
        except KernelTraceUnavailable:
            if tracer == "procfs":
                raise

    return PerfStatTraceRunner(
        command=command,
        page_allocator=page_allocator,
        total_ticks=total_ticks,
    ).execute_and_trace()


def _require_linux_proc():
    if platform.system() != "Linux" or not os.path.exists("/proc"):
        raise KernelTraceUnavailable("Kernel-level tracing currently requires Linux with procfs")


def _read_proc_faults(pid: int) -> Optional[tuple[int, int]]:
    stat_path = f"/proc/{pid}/stat"
    try:
        with open(stat_path, "r", encoding="utf-8") as stat_file:
            data = stat_file.read()
    except FileNotFoundError:
        return None

    end_comm = data.rfind(")")
    if end_comm == -1:
        return None
    fields = data[end_comm + 2 :].split()
    if len(fields) < 10:
        return None

    minflt = int(fields[7])
    majflt = int(fields[9])
    return minflt, majflt


def _parse_perf_stat(stderr: str) -> KernelTraceStats:
    stats = KernelTraceStats(source="perf")
    for line in stderr.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        value_text, _, event_name = parts[:3]
        if not value_text or value_text.startswith("<"):
            continue
        try:
            value = int(value_text.replace(",", ""))
        except ValueError:
            continue
        stats.raw_perf_counters[event_name] = value
        if event_name == "page-faults":
            stats.page_faults = value
        elif event_name == "minor-faults":
            stats.minor_faults = value
        elif event_name == "major-faults":
            stats.major_faults = value
        elif event_name == "cache-misses":
            stats.cache_misses = value
    return stats


def _parse_perf_script_addresses(stdout: str) -> list[int]:
    addresses = []
    for line in stdout.splitlines():
        for token in line.replace(",", " ").split():
            if not token.startswith("0x"):
                continue
            try:
                address = int(token, 16)
            except ValueError:
                continue
            if address > 0:
                addresses.append(address)
                break
    return addresses


def _events_from_sampled_addresses(
    sampled_addresses: Sequence[int],
    total_ticks: int,
    page_allocator: Callable[[PageType], Optional[Page]],
) -> tuple[list[tuple[int, Page]], int]:
    if not sampled_addresses:
        return [], 0

    page_by_address: dict[int, Page] = {}
    events = []
    event_count = len(sampled_addresses)
    for index, address in enumerate(sampled_addresses):
        page_key = address // 4096
        page = page_by_address.get(page_key)
        if page is None:
            page = page_allocator(PageType.ANON)
            if page is None:
                continue
            page_by_address[page_key] = page
        tick = int(index * max(total_ticks - 1, 1) / max(event_count - 1, 1))
        events.append((tick, page))
    return events, len(page_by_address)


def _events_from_aggregate_faults(
    page_faults: int,
    major_faults: int,
    total_ticks: int,
    page_allocator: Callable[[PageType], Optional[Page]],
    rng: random.Random,
) -> list[tuple[int, Page]]:
    if page_faults <= 0:
        return []

    events = []
    pages = []
    event_count = min(page_faults, max(total_ticks, 1))
    for index in range(event_count):
        page_type = PageType.FILE if index < major_faults else PageType.ANON
        page = page_allocator(page_type)
        if page is None:
            if pages:
                page = rng.choice(pages)
            else:
                continue
        else:
            pages.append(page)
        tick = int(index * max(total_ticks - 1, 1) / max(event_count - 1, 1))
        events.append((tick, page))
    return events
