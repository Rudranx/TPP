"""
Active / Inactive LRU lists management.
Paper uses separate LRU lists for anon and file pages; we unify for simplicity.
"""
from collections import deque
from .page import Page

class LRUList:
    def __init__(self):
        self.active = deque()     # most recently used pages
        self.inactive = deque()   # pages not recently used

    def add_page(self, page: Page, is_active: bool = True):
        """Insert page into the appropriate list."""
        if is_active:
            self.active.append(page)
        else:
            self.inactive.append(page)
        page.is_active = is_active

    def reference(self, page: Page):
        """Called when a page is accessed. Moves page to active list."""
        if page in self.active:
            # Move to end (most recent)
            self.active.remove(page)
            self.active.append(page)
        elif page in self.inactive:
            self.inactive.remove(page)
            self.active.append(page)
            page.is_active = True

    def move_to_inactive(self, page: Page):
        """Move a page from active to inactive (aging)."""
        if page in self.active:
            self.active.remove(page)
            self.inactive.append(page)
            page.is_active = False

    def get_lru_inactive(self, num: int) -> list:
        """Return up to `num` pages from the inactive list (front = oldest)."""
        res = []
        while self.inactive and len(res) < num:
            res.append(self.inactive[0])
            self.inactive.popleft()
        return res

    def remove(self, page: Page):
        """Remove a page from LRU (e.g., on migration)."""
        if page in self.active:
            self.active.remove(page)
        elif page in self.inactive:
            self.inactive.remove(page)