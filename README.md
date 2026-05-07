# TPP: Transparent Page Placement Simulator

Research-oriented simulator for Transparent Page Placement in CXL-enabled
tiered memory systems.

## Run Synthetic Simulation

```powershell
cd C:\code\Mini
py -m tpp.main
```

## Run RSS-Based Benchmark Approximation

```powershell
cd C:\code\Mini
py -m tpp.main --benchmark-script tpp\benchmarks\alloc_stress.py
```

## Start Kernel-Level Instrumentation

Kernel tracing is Linux-only. It currently supports:

- `procfs`: live `/proc/<pid>/stat` sampling for minor/major page fault deltas.
- `perf`: `perf stat` wrapping for aggregate `page-faults`, `minor-faults`,
  `major-faults`, and `cache-misses`.
- `auto`: starts with `procfs` and falls back to `perf` if needed.

Example on Linux:

```bash
python -m tpp.main --kernel-tracer procfs --kernel-trace python tpp/benchmarks/alloc_stress.py
```

Perf backend:

```bash
python -m tpp.main --kernel-tracer perf --kernel-trace python tpp/benchmarks/alloc_stress.py
```

This branch starts OS/perf/kernel-level instrumentation, but it still maps
kernel-observed counters into simulator events. Exact hardware page-reference
streams require a future eBPF or `perf mem` sampling backend.
