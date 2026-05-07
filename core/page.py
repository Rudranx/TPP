"""
Page representation: holds type, tier, LRU status, and access history.
"""
from enum import Enum, auto

class PageType(Enum):
    ANON = auto()   # heap/stack, mmap private
    FILE = auto()   # page cache

class Page:
    id_counter = 0

    def __init__(self, page_type: PageType = PageType.ANON):
        Page.id_counter += 1
        self.id = Page.id_counter
        self.page_type = page_type
        self.tier = None                # MemoryTier instance
        self.is_active = True           # True → active LRU, False → inactive
        self.last_access_tick = 0
        self.heat = 0.0                 # for Chameleon tracking
        self.demoted = False            # PG_demoted flag (§5.5)
        self.promoted_count = 0

    def access(self, tick: int, decay: float = 0.95):
        """Record an access to this page at the given tick."""
        self.last_access_tick = tick
        # Update heat for Chameleon analysis (not used for LRU decisions)
        self.heat = (self.heat + 1) * decay

    def __repr__(self):
        return f"Page(id={self.id}, type={self.page_type.name}, tier={self.tier.name if self.tier else 'None'})"
