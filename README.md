# TPP Benchmarking Simulator

This project is a research-oriented simulator inspired by the ASPLOS 2023 TPP
paper, "Transparent Page Placement for CXL-Enabled Tiered-Memory".

It can run synthetic traces, execute workload code, convert runtime memory
behavior into simulated page traces, and generate TPP-style outputs for
DRAM/CXL placement.

## Run Default Synthetic Simulation

```powershell
cd C:\code\Mini
py -m tpp.main
```

## Run Built-In Benchmark Suite

The built-in suite includes:

- web service request workload
- ads/recommendation workload
- data-structure traversal workload
- analytics workload
- cache/key-value workload

```powershell
cd C:\code\Mini
py -m tpp.main --benchmark-suite
```

Outputs are written to:

```text
benchmark_results/
```

The aggregate files are:

- `benchmark_results/index.html`
- `benchmark_results/summary.csv`
- `benchmark_results/summary.json`

Each workload also gets its own graph and report directory.

## Run Uploaded/User Workload Files

Pass one or more Python workload files:

```powershell
py -m tpp.main --workload-file path\to\web_code.py --workload-file path\to\ads_code.py
```

The framework executes each file, samples process memory growth, maps runtime
memory behavior into simulated TPP page events, and reports:

- DRAM hit rate
- average access latency
- DRAM/CXL usage
- promotions and demotions
- reuse distance
- working-set size
- heat distribution

## Current Limitation

On the `main` branch, workload execution uses RSS sampling through `psutil`.
This is enough for a portable project demo and benchmark framework, but it is
not exact hardware page-reference tracing. The `kernellevel` branch starts
Linux `/proc`, `perf stat`, and `perf mem` instrumentation.
