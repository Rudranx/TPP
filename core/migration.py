"""
Migration engine: handles demotion and promotion logic.
Uses LRU lists and watermarks to decide.
"""
from .page import Page, PageType
from .memory_tier import MemoryTier
from .lru_list import LRUList
from .watermark import WatermarkController

class MigrationEngine:
    def __init__(self, dram: MemoryTier, cxl: MemoryTier, lru: LRUList, wm: WatermarkController, config):
        self.dram = dram
        self.cxl = cxl
        self.lru = lru
        self.wm = wm
        self.config = config
        # Stats
        self.demotion_count = 0
        self.promotion_count = 0
        self.promotion_attempts = 0
        self.failed_promotions = 0

    def demote_batch(self):
        """Demote coldest inactive pages from DRAM to CXL if needed."""
        if not self.wm.need_demotion():
            return
        # Get pages from LRU inactive list (coldest)
        candidates = self.lru.get_lru_inactive(self.config.DEMOTION_BATCH_SIZE)
        candidates.sort(key=lambda page: page.heat)
        for page in candidates:
            if page.tier == self.dram:
                if page.heat > self.config.DEMOTION_HEAT_THRESHOLD and self.dram.free_space >= self.wm.low_watermark:
                    self.lru.add_page(page, is_active=False)
                    continue
                self.dram.remove_page(page)
                if self.cxl.add_page(page):
                    self.demotion_count += 1
                    page.demoted = True          # set PG_demoted flag
                    self.lru.add_page(page, is_active=False)
                else:
                    # CXL full -> fallback (do nothing in simulation)
                    # In paper, fallback to normal reclaim (swap), we ignore.
                    self.dram.add_page(page)
                    self.lru.add_page(page, is_active=False)

    def promote_page(self, page: Page):
        """Promote a page from CXL to DRAM if conditions allow.
        Promotion ignores allocation watermark to avoid deadlock (paper §5.3)."""
        if page.tier != self.cxl:
            return
        if not page.is_active or page.heat < self.config.PROMOTION_HEAT_THRESHOLD:
            return
        if self.dram.is_full():
            # If DRAM is full, promotion fails (we don't swap pages here)
            self.failed_promotions += 1
            return
        # Perform promotion
        self.promotion_attempts += 1
        self.cxl.remove_page(page)
        self.dram.add_page(page)
        self.promotion_count += 1
        page.demoted = False          # clear PG_demoted
        # On promotion, page becomes active (LRU reference)
        self.lru.reference(page)

    def decide_allocation_tier(self, page_type: PageType) -> MemoryTier:
        """
        Choose tier for a new page allocation.
        Implements page-type-aware allocation (§5.4).
        """
        if page_type == PageType.ANON and self.config.ANON_PREFER_DRAM:
            if self.wm.can_allocate():
                return self.dram
        elif page_type == PageType.FILE and self.config.FILE_PREFER_CXL:
            if not self.cxl.is_full():
                return self.cxl
        # Fallback: DRAM if possible, else CXL
        if self.wm.can_allocate():
            return self.dram
        elif not self.cxl.is_full():
            return self.cxl
        # Both full – should not happen if capacities are sufficient
        return None
