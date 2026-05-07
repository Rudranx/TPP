"""
NUMA hint fault scanner: simulates NUMA balancing on CXL nodes only.
Paper §5.3: only CXL pages are scanned, and only active-LRU pages are promoted.
"""
import random
from .page import Page
from .memory_tier import MemoryTier
from .lru_list import LRUList
from .migration import MigrationEngine

class NumaFaultScanner:
    def __init__(self, cxl: MemoryTier, lru: LRUList, migration: MigrationEngine, config):
        self.cxl = cxl
        self.lru = lru
        self.migration = migration
        self.scan_size = config.NUMA_SCAN_SIZE_PAGES
        self.period = config.NUMA_SCAN_PERIOD_TICKS

    def tick(self, current_tick: int):
        """Periodically scan a random subset of CXL pages for promotion."""
        if current_tick % self.period != 0:
            return
        # Get all CXL pages
        cxl_pages = list(self.cxl.pages)
        if not cxl_pages:
            return
        # Randomly sample a subset (simulating scanning)
        sample = random.sample(cxl_pages, min(self.scan_size, len(cxl_pages)))
        for page in sample:
            # Simulate a NUMA hint fault: the page was accessed from a CPU local to DRAM
            # The paper checks if the page is in active LRU
            if page.is_active:  # page was recently referenced (active list)
                # Promote immediately
                self.migration.promote_page(page)
            else:
                # Page is inactive. Do not promote, but move to active to give a second chance.
                self.lru.reference(page)   # moves it to active list (paper §5.3, "mark as accessed")
                # Next time it's sampled, it will be active and promoted.