"""
Benchmark suite orchestration for TPP evaluation.

This module runs multiple workload programs, converts their runtime memory
behavior into simulator traces, and writes per-workload plus aggregate reports.
"""
import csv
import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .config import Config
from .core import TPPSimulator
from .core.page import PageType
from .workload import command_for_python_script, run_real_workload
from .visualization import (
    plot_access_distribution,
    plot_heat_distribution,
    plot_heatmap,
    plot_hit_rate,
    plot_latency,
    plot_latency_comparison,
    plot_memory_usage,
    plot_migrations,
    plot_reuse_distance,
    plot_tier_composition,
    plot_working_set,
    write_html_report,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_BENCHMARKS = {
    "web": PACKAGE_ROOT / "benchmarks" / "web_workload.py",
    "ads": PACKAGE_ROOT / "benchmarks" / "ads_workload.py",
    "hashmap": PACKAGE_ROOT / "benchmarks" / "hashmap_workload.py",
    "graph": PACKAGE_ROOT / "benchmarks" / "graph_workload.py",
    "matrix": PACKAGE_ROOT / "benchmarks" / "matrix_workload.py",
    "cache": PACKAGE_ROOT / "benchmarks" / "cache_workload.py",
}


@dataclass
class BenchmarkResult:
    name: str
    script: str
    events: int
    dram_accesses: int
    cxl_accesses: int
    hit_rate: float
    avg_latency_ns: float
    demotions: int
    promotions: int
    dram_used: int
    cxl_used: int
    avg_reuse_distance: float
    working_set_pages: int
    unique_pages: int
    working_set_stability: float
    temporal_locality: str
    spatial_locality: str
    output_dir: str


def run_benchmark_suite(
    scripts: Iterable[Path],
    results_dir: Path,
    sample_interval_sec: float = 0.05,
    accesses_per_sample: int = 32,
) -> list[BenchmarkResult]:
    results_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for script in scripts:
        result = run_one_benchmark(
            script=Path(script),
            output_dir=results_dir / Path(script).stem,
            sample_interval_sec=sample_interval_sec,
            accesses_per_sample=accesses_per_sample,
        )
        results.append(result)

    write_aggregate_outputs(results, results_dir)
    return results


def run_default_suite(
    results_dir: Path,
    sample_interval_sec: float = 0.05,
    accesses_per_sample: int = 32,
) -> list[BenchmarkResult]:
    return run_benchmark_suite(
        scripts=DEFAULT_BENCHMARKS.values(),
        results_dir=results_dir,
        sample_interval_sec=sample_interval_sec,
        accesses_per_sample=accesses_per_sample,
    )


def run_one_benchmark(
    script: Path,
    output_dir: Path,
    sample_interval_sec: float,
    accesses_per_sample: int,
) -> BenchmarkResult:
    if not script.exists():
        raise FileNotFoundError(f"Benchmark script not found: {script}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    sim = TPPSimulator(cfg)
    workload = run_real_workload(
        command=command_for_python_script(str(script)),
        page_allocator=lambda page_type: sim.allocate_page(page_type),
        total_ticks=cfg.TOTAL_TICKS,
        sample_interval_sec=sample_interval_sec,
        accesses_per_sample=accesses_per_sample,
    )
    sim.run(workload)
    write_trace_csv(workload, output_dir / "trace.csv")
    write_workload_outputs(sim, output_dir)

    locality = sim.chameleon.locality_summary()
    classes = sim.chameleon.locality_classification()
    return BenchmarkResult(
        name=script.stem,
        script=str(script),
        events=len(workload),
        dram_accesses=sim.metrics.dram_accesses,
        cxl_accesses=sim.metrics.cxl_accesses,
        hit_rate=sim.metrics.final_hit_rate,
        avg_latency_ns=sim.metrics.final_avg_latency_ns,
        demotions=sim.metrics.demotions,
        promotions=sim.metrics.promotions,
        dram_used=sim.metrics.final_dram_used,
        cxl_used=sim.metrics.final_cxl_used,
        avg_reuse_distance=locality["avg_reuse_distance"],
        working_set_pages=locality["working_set_pages"],
        unique_pages=locality["unique_pages"],
        working_set_stability=classes["working_set_stability"],
        temporal_locality=classes["temporal_locality"],
        spatial_locality=classes["spatial_locality"],
        output_dir=str(output_dir),
    )


def write_workload_outputs(sim: TPPSimulator, output_dir: Path):
    plot_hit_rate(sim.metrics, save_path=str(output_dir / "hit_rate.png"))
    plot_latency(sim.metrics, save_path=str(output_dir / "latency.png"))
    plot_memory_usage(sim.metrics, save_path=str(output_dir / "memory_usage.png"))
    plot_migrations(sim.metrics, save_path=str(output_dir / "migrations.png"))
    plot_reuse_distance(sim.chameleon, save_path=str(output_dir / "reuse_distance.png"))
    plot_working_set(sim.chameleon, save_path=str(output_dir / "working_set.png"))
    plot_heat_distribution(sim.dram.pages + sim.cxl.pages, save_path=str(output_dir / "heat_distribution.png"))
    plot_heatmap(sim.dram.pages + sim.cxl.pages, save_path=str(output_dir / "heatmap.png"))
    plot_access_distribution(sim.chameleon, save_path=str(output_dir / "access_distribution.png"))
    plot_tier_composition(sim, save_path=str(output_dir / "tier_composition.png"))
    plot_latency_comparison(sim, save_path=str(output_dir / "latency_comparison.png"))
    write_html_report(sim, output_path=str(output_dir / "tpp_report.html"))


def write_trace_csv(workload: list, output_path: Path):
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["time", "page_id", "access_type", "page_type"])
        for tick, page in workload:
            writer.writerow([tick, page.id, "read", page.page_type.name])


def write_aggregate_outputs(results: list[BenchmarkResult], results_dir: Path):
    json_path = results_dir / "summary.json"
    csv_path = results_dir / "summary.csv"
    html_path = results_dir / "index.html"

    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump([asdict(result) for result in results], json_file, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(asdict(results[0]).keys()) if results else [])
        if results:
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))

    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(result.name)}</td>"
        f"<td>{result.events}</td>"
        f"<td>{result.hit_rate:.2%}</td>"
        f"<td>{result.avg_latency_ns:.2f}</td>"
        f"<td>{result.demotions}</td>"
        f"<td>{result.promotions}</td>"
        f"<td>{result.working_set_pages}</td>"
        f"<td>{result.temporal_locality}</td>"
        f"<td>{result.spatial_locality}</td>"
        f"<td><a href='{html.escape(Path(result.output_dir).name)}/tpp_report.html'>report</a></td>"
        "</tr>"
        for result in results
    )
    document = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TPP Benchmark Suite</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    table {{ border-collapse: collapse; min-width: 900px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
  </style>
</head>
<body>
  <h1>TPP Benchmark Suite</h1>
  <table>
    <tr>
      <th>Workload</th><th>Events</th><th>DRAM hit rate</th>
      <th>Avg latency ns</th><th>Demotions</th><th>Promotions</th>
      <th>Working set pages</th><th>Temporal locality</th>
      <th>Spatial locality</th><th>Details</th>
    </tr>
    {rows}
  </table>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as html_file:
        html_file.write(document)
