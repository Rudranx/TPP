"""
Chameleon-inspired page activity and locality tracking.

The tracker keeps interval bitmaps for hot/cold classification and also
records reuse distance and working-set size for evaluation graphs.
"""
from collections import defaultdict, deque


class ChameleonTracker:
    def __init__(self, interval_ticks: int = 100):
        self.interval_ticks = interval_ticks
        self.current_interval = 0
        self.page_bitmaps = defaultdict(int)
        self.page_access_counts = defaultdict(int)
        self.last_access_tick_by_page = {}
        self.reuse_distance_series = []
        self.working_set_series = []
        self._interval_pages = set()
        self._recent_pages = deque(maxlen=1024)

    def record_access(self, page, tick: int):
        interval = tick // self.interval_ticks
        while self.current_interval < interval:
            self._next_interval()

        self.page_bitmaps[page.id] |= 1
        self.page_access_counts[page.id] += 1
        self._interval_pages.add(page.id)

        previous_tick = self.last_access_tick_by_page.get(page.id)
        if previous_tick is not None:
            self.reuse_distance_series.append((tick, tick - previous_tick))
        self.last_access_tick_by_page[page.id] = tick

        self._recent_pages.append(page.id)

    def _next_interval(self):
        self.working_set_series.append((self.current_interval, len(self._interval_pages)))
        self._interval_pages.clear()
        self.current_interval += 1
        for pid in list(self.page_bitmaps.keys()):
            self.page_bitmaps[pid] = (self.page_bitmaps[pid] << 1) & 0xFFFFFFFFFFFFFFFF

    def finalize(self):
        self.working_set_series.append((self.current_interval, len(self._interval_pages)))

    def get_cold_pages(self, cold_threshold_intervals=2):
        """Return page IDs not accessed in the last N Chameleon intervals."""
        cold = []
        mask = (1 << cold_threshold_intervals) - 1
        for pid, bitmap in self.page_bitmaps.items():
            if (bitmap & mask) == 0:
                cold.append(pid)
        return cold

    def locality_summary(self):
        distances = [distance for _, distance in self.reuse_distance_series]
        if not distances:
            return {
                "avg_reuse_distance": 0,
                "max_reuse_distance": 0,
                "working_set_pages": 0,
                "unique_pages": len(self.page_bitmaps),
            }
        return {
            "avg_reuse_distance": sum(distances) / len(distances),
            "max_reuse_distance": max(distances),
            "working_set_pages": len(set(self._recent_pages)),
            "unique_pages": len(self.page_bitmaps),
        }

    def locality_classification(self):
        summary = self.locality_summary()
        avg_reuse = summary["avg_reuse_distance"]
        working_set = summary["working_set_pages"]
        unique_pages = max(1, summary["unique_pages"])
        working_set_stability = working_set / unique_pages

        if avg_reuse <= self.interval_ticks:
            temporal = "HIGH"
        elif avg_reuse <= self.interval_ticks * 5:
            temporal = "MODERATE"
        else:
            temporal = "LOW"

        if working_set_stability <= 0.35:
            spatial = "HIGH"
        elif working_set_stability <= 0.70:
            spatial = "MODERATE"
        else:
            spatial = "LOW"

        return {
            "working_set_stability": working_set_stability,
            "temporal_locality": temporal,
            "spatial_locality": spatial,
        }
