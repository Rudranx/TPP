"""
Collects simulation metrics for plots and reports.
"""


class MetricsCollector:
    def __init__(self):
        self.dram_accesses = 0
        self.cxl_accesses = 0
        self.total_accesses = 0
        self.demotions = 0
        self.promotions = 0
        self.promotion_attempts = 0
        self.total_latency_ns = 0

        self.hit_rate_series = []
        self.latency_series = []
        self.dram_used_series = []
        self.cxl_used_series = []
        self.migration_series = []

    def record_dram_access(self, latency_ns: float):
        self.dram_accesses += 1
        self.total_accesses += 1
        self.total_latency_ns += latency_ns

    def record_cxl_access(self, latency_ns: float):
        self.cxl_accesses += 1
        self.total_accesses += 1
        self.total_latency_ns += latency_ns

    def tick(self, tick: int, dram, cxl, demotions: int, promotions: int, attempts: int):
        self.demotions = demotions
        self.promotions = promotions
        self.promotion_attempts = attempts
        hit = self.dram_accesses / max(1, self.total_accesses)
        avg_latency = self.total_latency_ns / max(1, self.total_accesses)
        self.hit_rate_series.append((tick, hit))
        self.latency_series.append((tick, avg_latency))
        self.dram_used_series.append((tick, dram.used_pages))
        self.cxl_used_series.append((tick, cxl.used_pages))
        self.migration_series.append((tick, demotions, promotions))

    def finalize(self, dram, cxl):
        self.final_hit_rate = self.dram_accesses / max(1, self.total_accesses)
        self.final_avg_latency_ns = self.total_latency_ns / max(1, self.total_accesses)
        self.final_dram_used = dram.used_pages
        self.final_cxl_used = cxl.used_pages
