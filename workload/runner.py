"""
Execution of external benchmark workloads and conversion to simulator traces.

This runner observes a child process through RSS samples. It cannot see real
hardware page references, so it converts memory growth and continued residency
into a coarse sequence of simulated anonymous-page accesses.
"""
import random
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from typing import Optional

import psutil

from ..core.page import Page, PageType


PAGE_SIZE_BYTES = 4096


class RealWorkloadRunner:
    def __init__(
        self,
        command: Sequence[str],
        page_allocator: Callable[[PageType], Optional[Page]],
        total_ticks: int,
        sample_interval_sec: float = 0.1,
        accesses_per_sample: int = 16,
        seed: int = 7,
    ):
        self.command = list(command)
        self.page_allocator = page_allocator
        self.total_ticks = total_ticks
        self.sample_interval_sec = sample_interval_sec
        self.accesses_per_sample = accesses_per_sample
        self.random = random.Random(seed)

    def execute_and_trace(self) -> list[tuple[int, Page]]:
        """
        Run the benchmark command and return (tick, Page) events.

        RSS growth is converted into new anonymous pages. Each sample also
        touches a bounded working set so long-running benchmarks produce reuse.
        """
        if not self.command:
            raise ValueError("Benchmark command cannot be empty")

        process = psutil.Popen(
            self.command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        trace: list[tuple[int, Page]] = []
        pages: list[Page] = []
        peak_rss = self._rss_with_children(process)
        tick = 0

        try:
            while process.poll() is None and tick < self.total_ticks:
                rss = self._rss_with_children(process)
                if rss > peak_rss:
                    new_pages = (rss - peak_rss + PAGE_SIZE_BYTES - 1) // PAGE_SIZE_BYTES
                    for _ in range(new_pages):
                        page = self.page_allocator(PageType.ANON)
                        if page is not None:
                            pages.append(page)
                    peak_rss = rss

                if pages:
                    sample_size = min(self.accesses_per_sample, len(pages))
                    for page in self.random.sample(pages, sample_size):
                        trace.append((tick, page))

                tick += 1
                time.sleep(self.sample_interval_sec)
        finally:
            process.wait()

        if process.returncode != 0:
            raise RuntimeError(
                "Benchmark command failed with exit code "
                f"{process.returncode}"
            )

        return trace

    @staticmethod
    def _rss_with_children(process: psutil.Popen) -> int:
        try:
            rss = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    rss += child.memory_info().rss
                except psutil.Error:
                    continue
            return rss
        except psutil.Error:
            return 0


def command_for_python_script(script_path: str) -> list[str]:
    return [sys.executable, script_path]


def run_real_workload(
    command: Sequence[str],
    page_allocator: Callable[[PageType], Optional[Page]],
    total_ticks: int,
    sample_interval_sec: float = 0.1,
    accesses_per_sample: int = 16,
) -> list[tuple[int, Page]]:
    runner = RealWorkloadRunner(
        command=command,
        page_allocator=page_allocator,
        total_ticks=total_ticks,
        sample_interval_sec=sample_interval_sec,
        accesses_per_sample=accesses_per_sample,
    )
    return runner.execute_and_trace()
