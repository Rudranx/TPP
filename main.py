"""
Main entry point for TPP simulation.
Example:
    python -m tpp.main
    python -m tpp.main --benchmark-script path/to/benchmark.py
    python -m tpp.main --benchmark python benchmark.py
"""
import argparse

from .config import Config
from .core import TPPSimulator
from .core.page import PageType
from .workload import command_for_python_script, generate_synthetic_workload, run_real_workload
from .visualization import (
    plot_heat_distribution,
    plot_hit_rate,
    plot_latency,
    plot_memory_usage,
    plot_migrations,
    plot_reuse_distance,
    plot_working_set,
    write_html_report,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Run the TPP simulator.")
    parser.add_argument(
        "--benchmark-script",
        help="Python benchmark script to execute and convert into simulator events.",
    )
    parser.add_argument(
        "--benchmark",
        nargs=argparse.REMAINDER,
        help="External benchmark command. Put this option last.",
    )
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=0.1,
        help="Seconds between benchmark RSS samples.",
    )
    parser.add_argument(
        "--accesses-per-sample",
        type=int,
        default=16,
        help="Simulated page accesses emitted per benchmark sample.",
    )
    return parser.parse_args()


def allocate_simulated_page(sim: TPPSimulator, page_type: PageType):
    return sim.allocate_page(page_type)


def main():
    args = parse_args()
    cfg = Config()
    print("=== TPP Simulator ===")
    print(f"DRAM capacity: {cfg.DRAM_CAPACITY_PAGES} pages, CXL: {cfg.CXL_CAPACITY_PAGES} pages")
    print(f"Watermarks: alloc={cfg.ALLOCATION_WATERMARK_FRAC}, demote={cfg.DEMOTION_WATERMARK_FRAC}")
    print("=" * 40)

    # Create simulator
    sim = TPPSimulator(cfg)

    if args.benchmark_script and args.benchmark:
        raise SystemExit("Use either --benchmark-script or --benchmark, not both.")

    if args.benchmark_script or args.benchmark:
        command = command_for_python_script(args.benchmark_script) if args.benchmark_script else args.benchmark
        print(f"Running benchmark: {' '.join(command)}")
        workload = run_real_workload(
            command=command,
            page_allocator=lambda page_type: allocate_simulated_page(sim, page_type),
            total_ticks=cfg.TOTAL_TICKS,
            sample_interval_sec=args.sample_interval,
            accesses_per_sample=args.accesses_per_sample,
        )
        print(f"Captured {len(workload)} benchmark-derived access events")
    else:
        num_anon = 500
        num_file = 300
        workload = generate_synthetic_workload(num_anon, num_file, cfg.TOTAL_TICKS,
                                               hot_fraction=0.2, anon_hot_bias=0.8,
                                               page_allocator=lambda page_type: allocate_simulated_page(sim, page_type))
        print(f"Generated {len(workload)} access events over {cfg.TOTAL_TICKS} ticks")

    # Run simulation
    sim.run(workload)

    # Print final metrics
    print("\nFinal Metrics:")
    print(f"  DRAM accesses: {sim.metrics.dram_accesses}")
    print(f"  CXL accesses: {sim.metrics.cxl_accesses}")
    print(f"  Hit rate: {sim.metrics.final_hit_rate:.2%}")
    print(f"  Average latency: {sim.metrics.final_avg_latency_ns:.2f} ns")
    print(f"  Demotions: {sim.metrics.demotions}, Promotions: {sim.metrics.promotions}")
    print(f"  DRAM used: {sim.metrics.final_dram_used}, CXL used: {sim.metrics.final_cxl_used}")
    locality = sim.chameleon.locality_summary()
    print(f"  Avg reuse distance: {locality['avg_reuse_distance']:.2f} ticks")
    print(f"  Working set: {locality['working_set_pages']} pages")

    # Generate plots (if matplotlib is available)
    try:
        plot_hit_rate(sim.metrics, save_path="hit_rate.png")
        plot_latency(sim.metrics, save_path="latency.png")
        plot_memory_usage(sim.metrics, save_path="memory_usage.png")
        plot_migrations(sim.metrics, save_path="migrations.png")
        plot_reuse_distance(sim.chameleon, save_path="reuse_distance.png")
        plot_working_set(sim.chameleon, save_path="working_set.png")
        plot_heat_distribution(sim.dram.pages + sim.cxl.pages, save_path="heat_distribution.png")
        write_html_report(sim, output_path="tpp_report.html")
        print("Plots saved to hit_rate.png, latency.png, memory_usage.png, migrations.png, reuse_distance.png, working_set.png, heat_distribution.png")
        print("HTML report saved to tpp_report.html")
    except Exception as e:
        print(f"Plotting failed: {e}")

if __name__ == "__main__":
    main()
