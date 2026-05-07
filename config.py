"""
Global configuration for TPP simulation.
All parameters are taken from the paper where applicable.
"""

class Config:
    # Memory tier parameters (paper §2, §6)
    DRAM_CAPACITY_PAGES = 1000       # total DRAM pages (4KB pages for simplicity)
    CXL_CAPACITY_PAGES  = 4000       # 1:4 configuration
    DRAM_LATENCY_NS     = 100
    CXL_LATENCY_NS      = 220

    # Watermarks (paper §5.2)
    # Fractions of DRAM capacity
    ALLOCATION_WATERMARK_FRAC = 0.02  # default 2%
    DEMOTION_WATERMARK_FRAC    = 0.05  # higher, e.g. 5%
    LOW_WATERMARK_FRAC         = 0.01  # traditional Linux low watermark

    # LRU / aging (paper §5.3)
    AGING_INTERVAL_TICKS = 100        # simulation ticks between LRU aging passes
    ACTIVE_TO_INACTIVE_TIMEOUT = 100  # ticks without access before moving active→inactive

    # Promotion (paper §5.3)
    NUMA_SCAN_SIZE_PAGES = 256 * 256  # 256 MB of pages (4KB pages) ≈ 65536 pages
    NUMA_SCAN_PERIOD_TICKS = 1000     # how often we scan a subset of CXL pages

    # Demotion batch size (number of pages demoted per tick if needed)
    DEMOTION_BATCH_SIZE = 10

    # Page type bias (paper §5.4)
    ANON_PREFER_DRAM = True
    FILE_PREFER_CXL  = True

    # Heat decay (used in Chameleon tracker only, not for LRU-based decisions)
    HEAT_DECAY = 0.95
    PROMOTION_HEAT_THRESHOLD = 2.5
    DEMOTION_HEAT_THRESHOLD = 0.8

    # Simulation length
    TOTAL_TICKS = 5000
