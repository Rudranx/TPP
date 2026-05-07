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
- `perf-mem`: `perf mem record` plus `perf script` parsing for sampled hardware
  memory addresses mapped into simulator pages.
- `auto`: starts with `procfs` and falls back to `perf` if needed.

Example on Linux:

```bash
python -m tpp.main --kernel-tracer procfs --kernel-trace python tpp/benchmarks/alloc_stress.py
```

Perf backend:

```bash
python -m tpp.main --kernel-tracer perf --kernel-trace python tpp/benchmarks/alloc_stress.py
```

Perf memory-sampling backend:

```bash
python -m tpp.main --kernel-tracer perf-mem --kernel-trace python tpp/benchmarks/alloc_stress.py
```

`perf-mem` requires CPU PMU support and sufficient Linux perf permissions. It
captures sampled load/store memory addresses, not every hardware reference. A
future eBPF backend can add kernel migration/reclaim tracepoints alongside
these sampled hardware references.
