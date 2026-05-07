"""
Watermark controller: determines when to allow allocation and when to demote.
Based on paper §5.2.
"""
from .memory_tier import MemoryTier

class WatermarkController:
    def __init__(self, dram: MemoryTier, config):
        self.dram = dram
        self.allocation_watermark = int(dram.capacity * config.ALLOCATION_WATERMARK_FRAC)
        self.demotion_watermark   = int(dram.capacity * config.DEMOTION_WATERMARK_FRAC)
        self.low_watermark        = int(dram.capacity * config.LOW_WATERMARK_FRAC)

    def can_allocate(self) -> bool:
        """True if DRAM has enough free pages to allow new allocations."""
        return self.dram.free_space >= self.allocation_watermark

    def need_demotion(self) -> bool:
        """True if DRAM free space is below the demotion watermark."""
        return self.dram.free_space < self.demotion_watermark

    def below_low(self) -> bool:
        return self.dram.free_space < self.low_watermark