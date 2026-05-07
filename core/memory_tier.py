"""
Memory tier: DRAM or CXL. Holds pages and tracks free count.
"""
from typing import List
from .page import Page

class MemoryTier:
    def __init__(self, name: str, capacity_pages: int, latency_ns: float):
        self.name = name
        self.capacity = capacity_pages
        self.latency = latency_ns
        self.pages: List[Page] = []         # pages currently resident
        self.free_pages = capacity_pages    # initial free count

    @property
    def used_pages(self) -> int:
        return len(self.pages)

    @property
    def free_space(self) -> int:
        return self.capacity - self.used_pages

    def add_page(self, page: Page) -> bool:
        """Try to add a page to this tier. Returns True on success."""
        if self.used_pages >= self.capacity:
            return False
        self.pages.append(page)
        page.tier = self
        self.free_pages = self.capacity - self.used_pages
        return True

    def remove_page(self, page: Page):
        """Remove a page from this tier."""
        if page in self.pages:
            self.pages.remove(page)
            page.tier = None
            self.free_pages = self.capacity - self.used_pages

    def is_full(self) -> bool:
        return self.used_pages >= self.capacity

    def __repr__(self):
        return f"MemoryTier({self.name}, used={self.used_pages}/{self.capacity})"