# Validation record

Validated locally on macOS arm64 using actual Grafana 12.3.0, signed Business Text 6.3.0, Prometheus 3.5.0 and Alertmanager 0.28.1. Default hardware and workload feeds were simulated. No enterprise NVIDIA system or paid cloud account was provisioned.

## Automated behavior checks

`python3 -m unittest discover -s tests -v`: **16 tests passed**.

- Every one of the 68 catalog signals is emitted by its source contract.
- All ten scenarios, including the healthy control, produce the expected diagnostic domain.
- Counters remain monotonic across scenario changes.
- Histogram buckets are cumulative and the infinity bucket equals the request count.
- The analyzer attributes faults from observed measurements, without reading scenario names.
- Unrelated nodes and mixed telemetry origins do not form a fabric diagnosis.
- Native Prometheus/JSON/Redfish mapping and failed-live-feed handling were checked with controlled inputs.
- Metadata includes original documentation links and round-trips through the exposition format.
- Unsupported DCGM integer sentinels remain missing values, and a responding native endpoint without critical fields leaves its domain unknown.

## Actual stack integration

`python3 scripts/verify.py --faults` passed:

| Check | Result |
|---|---|
| Scrape health | All **15 targets** healthy: 14 source endpoints plus lab metadata |
| Dashboards | All four provisioned and retrievable from Grafana |
| Panel query syntax/execution | Every provisioned Prometheus query executed successfully |
| Controlled gray failure | `InfiniBandGrayFailure` reached firing state |
| Alert transport | Alertmanager delivered the firing alert to the local webhook ledger |
| Observed fault-to-webhook time | **18.14 seconds** in this run |
| Missing telemetry | UFM source-up became zero and InfiniBand domain became unknown |
| Restoration | Scenario reset to the healthy control after automated verification |

This latency is a measurement of this simulated lab run and its configured scrape/hold/routing periods. It is not a claim about real UFM acquisition cadence or hardware fault detection.

## Browser checks

The dashboards were inspected in actual Grafana using the default browser viewport, including Business Text rendering, source documentation links, topology nodes/edges, charts, gauges, request-latency heatmap, allocation bars, state/status history and the atlas table. Gallery images are screenshots of the running services, not design mockups.

Source-linked metric descriptions and panel links were verified in the UI. Visual inspection found and corrected an edge-schema issue in the topology graph and excessive point density in status history.

## Limits of this verification

The local machine has no Docker or NVIDIA GPU, so the native startup path was exercised here. The separate **Linux Docker Compose integration and unit jobs passed in GitHub Actions**: [verified run](https://github.com/sivalinb/ai-factory-observability-lab/actions/runs/38508048695). That run also verified generated-artifact reproducibility and Prometheus configuration/rules. Real DCGM/NIM workloads, proprietary NVIDIA endpoints, licenses and physical fabric faults require the corresponding hardware/access and remain unverified locally. The generic adapter transports and normalization contracts are implemented, but deployment-specific endpoint mappings still require validation against their installed releases.
