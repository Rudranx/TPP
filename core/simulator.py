"""
Main simulation loop. Orchestrates all components.
"""
from .page import Page, PageType
from .memory_tier import MemoryTier
from .lru_list import LRUList
from .watermark import WatermarkController
from .migration import MigrationEngine
from .numa_fault import NumaFaultScanner
from ..analysis.chameleon import ChameleonTracker
from ..analysis.metrics import MetricsCollector

class TPPSimulator:
    def __init__(self, config):
        self.config = config
        # Tiers
        self.dram = MemoryTier("DRAM", config.DRAM_CAPACITY_PAGES, config.DRAM_LATENCY_NS)
        self.cxl  = MemoryTier("CXL", config.CXL_CAPACITY_PAGES, config.CXL_LATENCY_NS)
        # LRU
        self.lru = LRUList()
        # Watermarks
        self.wm = WatermarkController(self.dram, config)
        # Migration engine
        self.migration = MigrationEngine(self.dram, self.cxl, self.lru, self.wm, config)
        # NUMA scanner
        self.numa_scanner = NumaFaultScanner(self.cxl, self.lru, self.migration, config)
        # Chameleon tracker
        self.chameleon = ChameleonTracker(interval_ticks=config.AGING_INTERVAL_TICKS)
        # Metrics
        self.metrics = MetricsCollector()

    def allocate_initial_pages(self, num_anon: int, num_file: int):
        """Pre-allocate a set of anon/file pages, placed according to policy."""
        for _ in range(num_anon):
            self.allocate_page(PageType.ANON)
        for _ in range(num_file):
            self.allocate_page(PageType.FILE)

    def allocate_page(self, page_type: PageType):
        """Allocate one page using simulator placement policy."""
        page = Page(page_type)
        tier = self.migration.decide_allocation_tier(page.page_type)
        if tier is None or not tier.add_page(page):
            return None
        self.lru.add_page(page, is_active=True)
        return page

    def tick(self, tick_num: int, accessed_page: Page):
        """Process one memory access at the given tick."""
        # 1. Page access
        page = accessed_page
        page.access(tick_num, decay=self.config.HEAT_DECAY)
        if page.tier == self.dram:
            self.metrics.record_dram_access(self.config.DRAM_LATENCY_NS)
        elif page.tier == self.cxl:
            self.metrics.record_cxl_access(self.config.CXL_LATENCY_NS)
        # Update LRU
        self.lru.reference(page)

        # 2. Chameleon tracking
        self.chameleon.record_access(page, tick_num)

        # 3. LRU aging: periodically move pages with no recent access from active to inactive
        if tick_num % self.config.AGING_INTERVAL_TICKS == 0:
            self._age_lru(tick_num)

        # 4. Demotion (asynchronous, every tick)
        self.migration.demote_batch()

        # 5. NUMA hint fault scanning (periodic)
        self.numa_scanner.tick(tick_num)

        # 6. Collect per‑interval metrics
        self.metrics.tick(tick_num, self.dram, self.cxl,
                          self.migration.demotion_count,
                          self.migration.promotion_count,
                          self.migration.promotion_attempts)

    def _age_lru(self, current_tick: int):
        """Move active pages that haven't been accessed for too long to inactive."""
        timeout = self.config.ACTIVE_TO_INACTIVE_TIMEOUT
        # We must iterate over a snapshot because we'll modify the list
        active_pages = list(self.lru.active)
        for page in active_pages:
            if current_tick - page.last_access_tick > timeout:
                self.lru.move_to_inactive(page)

    def run(self, workload_sequence):
        """Run the simulation over a sequence of (tick, page) events."""
        for tick, page in workload_sequence:
            self.tick(tick, page)
        self.chameleon.finalize()
        # Finalize metrics
        self.metrics.finalize(self.dram, self.cxl)
