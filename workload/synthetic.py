"""
Synthetic workload generator for TPP-style tiered-memory simulation.

The generator can either create standalone Page objects or allocate pages
through the simulator so accesses are counted against DRAM/CXL residency.
"""
import random
from collections.abc import Callable
from typing import Optional

from ..core.page import Page, PageType


def generate_synthetic_workload(
    num_anon: int,
    num_file: int,
    total_ticks: int,
    hot_fraction: float = 0.2,
    anon_hot_bias: float = 0.8,
    reuse_distance: int = 50,
    page_allocator: Optional[Callable[[PageType], Optional[Page]]] = None,
    seed: int = 42,
):
    """
    Produce a sequence of (tick, Page) events.

    Anonymous pages receive higher access weight to model the paper's
    observation that anonymous memory is generally hotter than file cache.
    """
    rng = random.Random(seed)
    allocator = page_allocator or (lambda page_type: Page(page_type))

    pages = []
    for _ in range(num_anon):
        page = allocator(PageType.ANON)
        if page is not None:
            pages.append(page)
    for _ in range(num_file):
        page = allocator(PageType.FILE)
        if page is not None:
            pages.append(page)

    if not pages:
        return []

    hot_set_size = max(1, int(len(pages) * hot_fraction))
    hot_pages = rng.sample(pages, k=hot_set_size)

    workload = []
    tick = 0
    while tick < total_ticks:
        candidates = hot_pages if rng.random() < 0.7 else pages
        weights = [
            3.0 if page.page_type == PageType.ANON else max(0.1, 3.0 * (1.0 - anon_hot_bias))
            for page in candidates
        ]
        page = rng.choices(candidates, weights=weights, k=1)[0]
        workload.append((tick, page))
        tick += rng.randint(1, reuse_distance)

    return workload
