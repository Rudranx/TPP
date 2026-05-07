import html
import math

import matplotlib.pyplot as plt


def _save_or_show(save_path):
    if save_path:
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


def plot_hit_rate(metrics, title="DRAM Hit Rate", save_path=None):
    ticks, rates = zip(*metrics.hit_rate_series) if metrics.hit_rate_series else ([], [])
    plt.figure()
    plt.plot(ticks, rates)
    plt.xlabel("Tick")
    plt.ylabel("Hit Rate")
    plt.title(title)
    plt.grid(True)
    _save_or_show(save_path)


def plot_latency(metrics, title="Average Access Latency", save_path=None):
    ticks, latencies = zip(*metrics.latency_series) if metrics.latency_series else ([], [])
    plt.figure()
    plt.plot(ticks, latencies)
    plt.xlabel("Tick")
    plt.ylabel("Latency (ns)")
    plt.title(title)
    plt.grid(True)
    _save_or_show(save_path)


def plot_memory_usage(metrics, title="Memory Usage", save_path=None):
    ticks_dram, dram_used = zip(*metrics.dram_used_series) if metrics.dram_used_series else ([], [])
    ticks_cxl, cxl_used = zip(*metrics.cxl_used_series) if metrics.cxl_used_series else ([], [])
    plt.figure()
    plt.plot(ticks_dram, dram_used, label="DRAM used")
    plt.plot(ticks_cxl, cxl_used, label="CXL used")
    plt.xlabel("Tick")
    plt.ylabel("Pages")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    _save_or_show(save_path)


def plot_migrations(metrics, title="Migrations", save_path=None):
    ticks, demotions, promotions = zip(*metrics.migration_series) if metrics.migration_series else ([], [], [])
    plt.figure()
    plt.plot(ticks, demotions, label="Demotions")
    plt.plot(ticks, promotions, label="Promotions")
    plt.xlabel("Tick")
    plt.ylabel("Pages")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    _save_or_show(save_path)


def plot_reuse_distance(chameleon, title="Reuse Distance", save_path=None):
    ticks, distances = zip(*chameleon.reuse_distance_series) if chameleon.reuse_distance_series else ([], [])
    plt.figure()
    plt.plot(ticks, distances)
    plt.xlabel("Tick")
    plt.ylabel("Ticks Since Previous Access")
    plt.title(title)
    plt.grid(True)
    _save_or_show(save_path)


def plot_working_set(chameleon, title="Working Set Size", save_path=None):
    intervals, sizes = zip(*chameleon.working_set_series) if chameleon.working_set_series else ([], [])
    plt.figure()
    plt.plot(intervals, sizes)
    plt.xlabel("Chameleon Interval")
    plt.ylabel("Unique Pages")
    plt.title(title)
    plt.grid(True)
    _save_or_show(save_path)


def plot_heat_distribution(pages, title="Page Heat Distribution", save_path=None):
    heats = [page.heat for page in pages]
    plt.figure()
    plt.hist(heats, bins=20)
    plt.xlabel("Heat")
    plt.ylabel("Pages")
    plt.title(title)
    plt.grid(True)
    _save_or_show(save_path)


def plot_heatmap(pages, title="Page Heatmap", save_path=None):
    heats = [page.heat for page in pages]
    if not heats:
        heats = [0]
    width = max(1, math.ceil(math.sqrt(len(heats))))
    padded = heats + [0] * ((width * width) - len(heats))
    grid = [padded[index:index + width] for index in range(0, len(padded), width)]
    plt.figure()
    plt.imshow(grid, cmap="inferno", aspect="auto")
    plt.colorbar(label="Heat")
    plt.title(title)
    plt.xlabel("Page bucket")
    plt.ylabel("Page bucket")
    _save_or_show(save_path)


def plot_access_distribution(chameleon, title="Access Distribution", save_path=None):
    counts = sorted(chameleon.page_access_counts.values(), reverse=True)
    plt.figure()
    plt.plot(range(1, len(counts) + 1), counts)
    plt.xlabel("Page rank")
    plt.ylabel("Access count")
    plt.title(title)
    plt.grid(True)
    _save_or_show(save_path)


def plot_tier_composition(sim, title="Final Tier Composition", save_path=None):
    plt.figure()
    plt.pie(
        [sim.dram.used_pages, sim.cxl.used_pages],
        labels=["DRAM", "CXL"],
        autopct="%1.1f%%",
        startangle=90,
    )
    plt.title(title)
    _save_or_show(save_path)


def plot_latency_comparison(sim, title="Latency Comparison", save_path=None):
    total = max(1, sim.metrics.total_accesses)
    all_dram = sim.config.DRAM_LATENCY_NS
    all_cxl = sim.config.CXL_LATENCY_NS
    tpp = sim.metrics.final_avg_latency_ns
    plt.figure()
    plt.bar(["All DRAM", "TPP", "All CXL"], [all_dram, tpp, all_cxl])
    plt.ylabel("Average latency (ns)")
    plt.title(title)
    plt.grid(axis="y")
    for index, value in enumerate([all_dram, tpp, all_cxl]):
        plt.text(index, value, f"{value:.1f}", ha="center", va="bottom")
    _save_or_show(save_path)


def write_html_report(sim, output_path="tpp_report.html"):
    locality = sim.chameleon.locality_summary()
    classes = sim.chameleon.locality_classification()
    rows = {
        "Total accesses": sim.metrics.total_accesses,
        "DRAM accesses": sim.metrics.dram_accesses,
        "CXL accesses": sim.metrics.cxl_accesses,
        "DRAM hit rate": f"{sim.metrics.final_hit_rate:.2%}",
        "Average latency": f"{sim.metrics.final_avg_latency_ns:.2f} ns",
        "Demotions": sim.metrics.demotions,
        "Promotions": sim.metrics.promotions,
        "DRAM used": sim.metrics.final_dram_used,
        "CXL used": sim.metrics.final_cxl_used,
        "Average reuse distance": f"{locality['avg_reuse_distance']:.2f} ticks",
        "Max reuse distance": locality["max_reuse_distance"],
        "Working set pages": locality["working_set_pages"],
        "Unique touched pages": locality["unique_pages"],
        "Working set stability": f"{classes['working_set_stability']:.2f}",
        "Temporal locality": classes["temporal_locality"],
        "Spatial locality": classes["spatial_locality"],
    }
    table = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in rows.items()
    )
    document = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TPP Evaluation Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    table {{ border-collapse: collapse; min-width: 520px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    img {{ max-width: 720px; display: block; margin: 20px 0; }}
  </style>
</head>
<body>
  <h1>TPP Evaluation Report</h1>
  <table>{table}</table>
  <h2>Graphs</h2>
  <img src="hit_rate.png" alt="DRAM hit rate">
  <img src="latency.png" alt="Average latency">
  <img src="memory_usage.png" alt="Memory usage">
  <img src="migrations.png" alt="Migrations">
  <img src="reuse_distance.png" alt="Reuse distance">
  <img src="working_set.png" alt="Working set">
  <img src="heat_distribution.png" alt="Heat distribution">
  <img src="heatmap.png" alt="Heatmap">
  <img src="access_distribution.png" alt="Access distribution">
  <img src="tier_composition.png" alt="Tier composition">
  <img src="latency_comparison.png" alt="Latency comparison">
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as report:
        report.write(document)
