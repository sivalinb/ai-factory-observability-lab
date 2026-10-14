# Signal atlas

Generated from `lab/catalog.py`. Every default feed is simulated. `lab_*` names are project normalization contracts, not claims about vendor exporter names.

Framework: [original NVIDIA article](https://developer.nvidia.com/blog/how-to-choose-full-stack-observability-for-nvidia-ai-factories/).

Native metric names are version-specific. Inspect the actual exporter output and apply explicit mappings. BMC wildcards in the article describe sensor labels, not universal Prometheus metric names.

## Redfish

Domain: platform. [Original documentation](https://redfish.dmtf.org/redfish/schema_index). Demo endpoint: `/metrics/redfish`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_redfish_fan_rpm` | gauge / rpm | Chassis fan rotation. Inspect cooling and fan status. | `Fan.Reading / Sensor.Reading; SPD_FAN_* sensor labels`; lab-defined normalized metric | [docs](https://redfish.dmtf.org/redfish/schema_index) |
| `lab_redfish_psu_healthy` | gauge / boolean | Power supply health: 1 healthy, 0 fault. Inspect the power supply and redundancy. | `PowerSupply.Status.Health; PWR_* sensor labels`; lab-defined normalized metric | [docs](https://redfish.dmtf.org/redfish/schema_index) |
| `lab_redfish_temperature_celsius` | gauge / celsius | Chassis sensor temperature. Check airflow and thermal limits. | `Sensor.Reading / Temperature.ReadingCelsius; TEMP_* sensor labels`; lab-defined normalized metric | [docs](https://redfish.dmtf.org/redfish/schema_index) |
| `lab_redfish_bmc_healthy` | gauge / boolean | BMC manager health. Investigate management-plane availability. | `Manager.Status.Health`; lab-defined normalized metric | [docs](https://redfish.dmtf.org/redfish/schema_index) |

<details><summary>Queries and cadence notes</summary>

**lab_redfish_fan_rpm** — 5

```promql
lab_redfish_fan_rpm
```

**lab_redfish_psu_healthy** — 5

```promql
lab_redfish_psu_healthy
```

**lab_redfish_temperature_celsius** — 5

```promql
lab_redfish_temperature_celsius
```

**lab_redfish_bmc_healthy** — 5

```promql
lab_redfish_bmc_healthy
```

</details>

## IPMI Exporter

Domain: platform. [Original documentation](https://github.com/prometheus-community/ipmi_exporter). Demo endpoint: `/metrics/ipmi`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `ipmi_fan_speed_rpm` | gauge / rpm | Fan sensor reading. Inspect sensor and BMC event log. | `SPD_FAN_*`; documented exporter name | [docs](https://github.com/prometheus-community/ipmi_exporter) |
| `ipmi_temperature_celsius` | gauge / celsius | Temperature sensor reading. Inspect sensor and BMC event log. | `TEMP_*`; documented exporter name | [docs](https://github.com/prometheus-community/ipmi_exporter) |
| `ipmi_sensor_state` | gauge / enum | IPMI sensor severity; demo 0 nominal, 1 warning, 2 critical. Inspect sensor and BMC event log. | `PWR_*`; documented exporter name | [docs](https://github.com/prometheus-community/ipmi_exporter) |

<details><summary>Queries and cadence notes</summary>

**ipmi_fan_speed_rpm** — 5

```promql
ipmi_fan_speed_rpm
```

**ipmi_temperature_celsius** — 5

```promql
ipmi_temperature_celsius
```

**ipmi_sensor_state** — 5

```promql
ipmi_sensor_state
```

</details>

## DCGM Exporter

Domain: gpu. [Original documentation](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html). Demo endpoint: `/metrics/dcgm`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `DCGM_FI_DEV_GPU_UTIL` | gauge / percent | GPU activity percentage. Compare to workload progress. | `DCGM_FI_DEV_GPU_UTIL`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | gauge / percent | Memory activity percentage. Check memory pressure. | `DCGM_FI_DEV_MEM_COPY_UTIL`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_POWER_USAGE` | gauge / watt | GPU board power draw. Compare to temperature and clocks. | `DCGM_FI_DEV_POWER_USAGE`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_GPU_TEMP` | gauge / celsius | GPU temperature. Inspect thermal throttling. | `DCGM_FI_DEV_GPU_TEMP`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_XID_ERRORS` | gauge / error code | Last observed XID code; not an event count. Classify XID and investigate the node. | `DCGM_FI_DEV_XID_ERRORS`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_ECC_DBE_VOL_TOTAL` | counter / errors | Volatile uncorrectable ECC count. Investigate GPU memory health. | `DCGM_FI_DEV_ECC_DBE_VOL_TOTAL`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL` | gauge / MB/s (legacy) | Legacy aggregate node NVLink throughput. Use the native byte/s field for base-unit analysis. | `DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_SM_CLOCK` | gauge / MHz | Streaming multiprocessor clock. Check clock limiting. | `DCGM_FI_DEV_SM_CLOCK`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_FB_USED` | gauge / MiB | Allocated framebuffer memory. Inspect memory headroom. | `DCGM_FI_DEV_FB_USED`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |
| `DCGM_FI_DEV_THERMAL_VIOLATION` | counter / nanosecond | Accumulated thermal limiting duration. Investigate cooling. | `DCGM_FI_DEV_THERMAL_VIOLATION`; documented exporter name | [docs](https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html) |

<details><summary>Queries and cadence notes</summary>

**DCGM_FI_DEV_GPU_UTIL** — 5

```promql
DCGM_FI_DEV_GPU_UTIL
```

**DCGM_FI_DEV_MEM_COPY_UTIL** — 5

```promql
DCGM_FI_DEV_MEM_COPY_UTIL
```

**DCGM_FI_DEV_POWER_USAGE** — 5

```promql
DCGM_FI_DEV_POWER_USAGE
```

**DCGM_FI_DEV_GPU_TEMP** — 5

```promql
DCGM_FI_DEV_GPU_TEMP
```

**DCGM_FI_DEV_XID_ERRORS** — 5

```promql
DCGM_FI_DEV_XID_ERRORS
```

**DCGM_FI_DEV_ECC_DBE_VOL_TOTAL** — 5

```promql
rate(DCGM_FI_DEV_ECC_DBE_VOL_TOTAL[2m])
```

**DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL** — 5

```promql
DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL
```

**DCGM_FI_DEV_SM_CLOCK** — 5

```promql
DCGM_FI_DEV_SM_CLOCK
```

**DCGM_FI_DEV_FB_USED** — 5

```promql
DCGM_FI_DEV_FB_USED
```

**DCGM_FI_DEV_THERMAL_VIOLATION** — 5

```promql
rate(DCGM_FI_DEV_THERMAL_VIOLATION[2m])
```

</details>

## NVIDIA System Management

Domain: platform. [Original documentation](https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html). Demo endpoint: `/metrics/nvsm`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_nvsm_system_healthy` | gauge / boolean | Overall DGX status. 1 healthy, 0 fault. Run NVSM health inspection. | `NVSM system health; map the installed release`; lab-defined normalized metric | [docs](https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html) |
| `lab_nvsm_storage_healthy` | gauge / boolean | Local drive/volume health. 1 healthy, 0 fault. Run NVSM health inspection. | `NVSM storage health; map the installed release`; lab-defined normalized metric | [docs](https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html) |
| `lab_nvsm_cpu_healthy` | gauge / boolean | CPU health. 1 healthy, 0 fault. Run NVSM health inspection. | `NVSM cpu health; map the installed release`; lab-defined normalized metric | [docs](https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html) |
| `lab_nvsm_memory_healthy` | gauge / boolean | DIMM health. 1 healthy, 0 fault. Run NVSM health inspection. | `NVSM memory health; map the installed release`; lab-defined normalized metric | [docs](https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html) |
| `lab_nvsm_pcie_healthy` | gauge / boolean | PCIe health. 1 healthy, 0 fault. Run NVSM health inspection. | `NVSM pcie health; map the installed release`; lab-defined normalized metric | [docs](https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html) |

<details><summary>Queries and cadence notes</summary>

**lab_nvsm_system_healthy** — 5

```promql
lab_nvsm_system_healthy
```

**lab_nvsm_storage_healthy** — 5

```promql
lab_nvsm_storage_healthy
```

**lab_nvsm_cpu_healthy** — 5

```promql
lab_nvsm_cpu_healthy
```

**lab_nvsm_memory_healthy** — 5

```promql
lab_nvsm_memory_healthy
```

**lab_nvsm_pcie_healthy** — 5

```promql
lab_nvsm_pcie_healthy
```

</details>

## UFM Telemetry

Domain: infiniband. [Original documentation](https://networking-docs.nvidia.com/ufmtelemetryum/1212/prometheus-endpoint-support). Demo endpoint: `/metrics/ufm`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_ufm_port_xmit_bytes_total` | counter / byte | Lab-integrated transmitted traffic in bytes. Inspect affected link in UFM; correlate to ranks. | `PortXmitDataExtended`; lab-defined normalized metric | [docs](https://networking-docs.nvidia.com/ufmenterpriseum/6244/high-frequency-primary-telemetry-fields) |
| `lab_ufm_symbol_errors_total` | counter / errors | Accumulated symbol errors. Inspect affected link in UFM; correlate to ranks. | `SymbolErrorCounterExtended`; lab-defined normalized metric | [docs](https://networking-docs.nvidia.com/ufmenterpriseum/6244/high-frequency-primary-telemetry-fields) |
| `lab_ufm_effective_ber_ratio` | gauge / ratio | Post-FEC bit error ratio. Inspect affected link in UFM; correlate to ranks. | `Effective_BER`; lab-defined normalized metric | [docs](https://networking-docs.nvidia.com/ufmenterpriseum/6244/low-frequency-secondary-telemetry-fields) |
| `lab_ufm_raw_ber_ratio` | gauge / ratio | Pre-FEC bit error ratio. Inspect affected link in UFM; correlate to ranks. | `Total_Raw_BER`; lab-defined normalized metric | [docs](https://networking-docs.nvidia.com/ufmenterpriseum/6244/low-frequency-secondary-telemetry-fields) |
| `lab_ufm_chip_temperature_celsius` | gauge / celsius | Switch chip temperature. Inspect affected link in UFM; correlate to ranks. | `Chip_Temp`; lab-defined normalized metric | [docs](https://networking-docs.nvidia.com/ufmenterpriseum/6244/low-frequency-secondary-telemetry-fields) |
| `lab_ufm_congestion_wait_seconds_total` | counter / second | Lab-integrated transmit-wait duration. Inspect affected link in UFM; correlate to ranks. | `PortXmitWaitExtended; requires device-specific conversion`; lab-defined normalized metric | [docs](https://networking-docs.nvidia.com/ufmenterpriseum/6244/high-frequency-primary-telemetry-fields) |

<details><summary>Queries and cadence notes</summary>

**lab_ufm_port_xmit_bytes_total** — UFM 6.24.4 describes sample-period bytes/data rate, not this cumulative lab counter. Integrate a validated rate; do not apply rate() to interval bytes.

```promql
rate(lab_ufm_port_xmit_bytes_total[2m])
```

**lab_ufm_symbol_errors_total** — Use a rate; allow counter resets.

```promql
rate(lab_ufm_symbol_errors_total[2m])
```

**lab_ufm_effective_ber_ratio** — Some UFM releases collect secondary fields every 300 seconds.

```promql
lab_ufm_effective_ber_ratio
```

**lab_ufm_raw_ber_ratio** — Pre-FEC errors alone do not establish workload impact.

```promql
lab_ufm_raw_ber_ratio
```

**lab_ufm_chip_temperature_celsius** — UFM 6.24.4 lists this as secondary telemetry; validate its collection cadence.

```promql
lab_ufm_chip_temperature_celsius
```

**lab_ufm_congestion_wait_seconds_total** — Sample-window ticks require conversion and accumulation using the installed device documentation.

```promql
rate(lab_ufm_congestion_wait_seconds_total[2m])
```

</details>

## NetQ Ethernet / RoCE

Domain: ethernet. [Original documentation](https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/). Demo endpoint: `/metrics/netq`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_netq_pfc_pause_seconds_total` | counter / second | Normalized PFC pause time. Inspect RoCE QoS, buffers and affected interface. | `Rx RoCE PFC pause duration`; lab-defined normalized metric | [docs](https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/) |
| `lab_netq_ecn_marked_packets_total` | counter / packets | ECN-marked traffic. Inspect RoCE QoS, buffers and affected interface. | `Tx ECN marked packets`; lab-defined normalized metric | [docs](https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/) |
| `lab_netq_dropped_packets_total` | counter / packets | Congestion-related drops. Inspect RoCE QoS, buffers and affected interface. | `Rx RoCE no buffer discard`; lab-defined normalized metric | [docs](https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/) |
| `lab_netq_link_flaps_total` | counter / events | Link state transitions. Inspect RoCE QoS, buffers and affected interface. | `Link flap errors`; lab-defined normalized metric | [docs](https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/) |
| `lab_netq_buffer_usage_ratio` | gauge / ratio | Normalized RoCE buffer occupancy. Inspect RoCE QoS, buffers and affected interface. | `Rx RoCE buffer usage`; lab-defined normalized metric | [docs](https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/) |

<details><summary>Queries and cadence notes</summary>

**lab_netq_pfc_pause_seconds_total** — 5

```promql
rate(lab_netq_pfc_pause_seconds_total[2m])
```

**lab_netq_ecn_marked_packets_total** — 5

```promql
rate(lab_netq_ecn_marked_packets_total[2m])
```

**lab_netq_dropped_packets_total** — 5

```promql
rate(lab_netq_dropped_packets_total[2m])
```

**lab_netq_link_flaps_total** — 5

```promql
rate(lab_netq_link_flaps_total[2m])
```

**lab_netq_buffer_usage_ratio** — 5

```promql
lab_netq_buffer_usage_ratio
```

</details>

## NMX / NetQ NVLink

Domain: nvlink. [Original documentation](https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html). Demo endpoint: `/metrics/nmx`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_nmx_link_healthy` | gauge / boolean | NVLink link health. Inspect NVSwitch domain and partition. | `NVLink link status; installed schema`; lab-defined normalized metric | [docs](https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html) |
| `lab_nmx_link_bytes_total` | counter / byte | Normalized NVLink traffic. Inspect NVSwitch domain and partition. | `NVLink throughput; installed schema`; lab-defined normalized metric | [docs](https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html) |
| `lab_nmx_link_errors_total` | counter / errors | Normalized NVLink errors. Inspect NVSwitch domain and partition. | `NVLink errors; installed schema`; lab-defined normalized metric | [docs](https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html) |
| `lab_nmx_partition_healthy` | gauge / boolean | NVLink partition health. Inspect NVSwitch domain and partition. | `NVLink partition Health`; lab-defined normalized metric | [docs](https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html) |

<details><summary>Queries and cadence notes</summary>

**lab_nmx_link_healthy** — 5

```promql
lab_nmx_link_healthy
```

**lab_nmx_link_bytes_total** — 5

```promql
rate(lab_nmx_link_bytes_total[2m])
```

**lab_nmx_link_errors_total** — 5

```promql
rate(lab_nmx_link_errors_total[2m])
```

**lab_nmx_partition_healthy** — 5

```promql
lab_nmx_partition_healthy
```

</details>

## Base Command Manager

Domain: scheduling. [Original documentation](https://docs.nvidia.com/base-command-manager/). Demo endpoint: `/metrics/bcm`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_bcm_running_jobs` | gauge / jobs | Running job count. Inspect placement, reservations and quota policy. | `bcm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/base-command-manager/) |
| `lab_bcm_reserved_gpus` | gauge / GPUs | Reserved GPU count. Inspect placement, reservations and quota policy. | `bcm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/base-command-manager/) |
| `lab_bcm_queue_wait_seconds` | gauge / second | Oldest pending job wait. Inspect placement, reservations and quota policy. | `bcm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/base-command-manager/) |
| `lab_bcm_idle_allocated_gpus` | gauge / GPUs | Allocated GPUs lacking useful progress. Inspect placement, reservations and quota policy. | `bcm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/base-command-manager/) |
| `lab_bcm_node_healthy` | gauge / boolean | Managed node health. Inspect placement, reservations and quota policy. | `bcm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/base-command-manager/) |

<details><summary>Queries and cadence notes</summary>

**lab_bcm_running_jobs** — 5

```promql
lab_bcm_running_jobs
```

**lab_bcm_reserved_gpus** — 5

```promql
lab_bcm_reserved_gpus
```

**lab_bcm_queue_wait_seconds** — 5

```promql
lab_bcm_queue_wait_seconds
```

**lab_bcm_idle_allocated_gpus** — 5

```promql
lab_bcm_idle_allocated_gpus
```

**lab_bcm_node_healthy** — 5

```promql
lab_bcm_node_healthy
```

</details>

## Slurm

Domain: scheduling. [Original documentation](https://slurm.schedmd.com/squeue.html). Demo endpoint: `/metrics/slurm`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_slurm_running_jobs` | gauge / jobs | Running Slurm jobs. Inspect placement, reservations and quota policy. | `slurm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://slurm.schedmd.com/squeue.html) |
| `lab_slurm_queue_wait_seconds` | gauge / second | Oldest pending Slurm job wait. Inspect placement, reservations and quota policy. | `slurm API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://slurm.schedmd.com/squeue.html) |

<details><summary>Queries and cadence notes</summary>

**lab_slurm_running_jobs** — 5

```promql
lab_slurm_running_jobs
```

**lab_slurm_queue_wait_seconds** — 5

```promql
lab_slurm_queue_wait_seconds
```

</details>

## NVIDIA Run:ai

Domain: scheduling. [Original documentation](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics). Demo endpoint: `/metrics/runai`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_runai_allocated_gpus` | gauge / GPUs | Project GPU allocation. Inspect placement, reservations and quota policy. | `runai API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics) |
| `lab_runai_quota_gpus` | gauge / GPUs | Project guaranteed quota. Inspect placement, reservations and quota policy. | `runai API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics) |
| `lab_runai_pending_jobs` | gauge / jobs | Pending workload count. Inspect placement, reservations and quota policy. | `runai API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics) |
| `lab_runai_queue_wait_seconds` | gauge / second | Oldest pending workload wait. Inspect placement, reservations and quota policy. | `runai API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics) |
| `lab_runai_idle_allocated_gpus` | gauge / GPUs | Allocated GPUs without useful progress. Inspect placement, reservations and quota policy. | `runai API/exporter concept; explicit installation mapping required`; lab-defined normalized metric | [docs](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics) |

<details><summary>Queries and cadence notes</summary>

**lab_runai_allocated_gpus** — 5

```promql
lab_runai_allocated_gpus
```

**lab_runai_quota_gpus** — 5

```promql
lab_runai_quota_gpus
```

**lab_runai_pending_jobs** — 5

```promql
lab_runai_pending_jobs
```

**lab_runai_queue_wait_seconds** — 5

```promql
lab_runai_queue_wait_seconds
```

**lab_runai_idle_allocated_gpus** — 5

```promql
lab_runai_idle_allocated_gpus
```

</details>

## NVIDIA NIM

Domain: inference. [Original documentation](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html). Demo endpoint: `/metrics/nim`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `gpu_cache_usage_perc` | gauge / ratio | GPU KV-cache occupancy, from 0 to 1. Compare demand, queueing and cache pressure. | `gpu_cache_usage_perc`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `num_requests_running` | gauge / requests | Executing inference requests. Compare demand, queueing and cache pressure. | `num_requests_running`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `num_requests_waiting` | gauge / requests | Queued inference requests. Compare demand, queueing and cache pressure. | `num_requests_waiting`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `request_success_total` | counter / requests | Successful model generations. Compare demand, queueing and cache pressure. | `request_success_total`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `request_failure_total` | counter / requests | Failed model generations. Compare demand, queueing and cache pressure. | `request_failure_total`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `generation_tokens_total` | counter / tokens | Generated output tokens. Compare demand, queueing and cache pressure. | `generation_tokens_total`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `time_to_first_token_seconds` | histogram / second | First-token latency distribution. Compare demand, queueing and cache pressure. | `time_to_first_token_seconds`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `time_per_output_token_seconds` | histogram / second | Output-token latency distribution. Compare demand, queueing and cache pressure. | `time_per_output_token_seconds`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |
| `e2e_request_latency_seconds` | histogram / second | Request completion latency distribution. Compare demand, queueing and cache pressure. | `e2e_request_latency_seconds`; documented exporter name | [docs](https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html) |

<details><summary>Queries and cadence notes</summary>

**gpu_cache_usage_perc** — 5

```promql
gpu_cache_usage_perc
```

**num_requests_running** — 5

```promql
num_requests_running
```

**num_requests_waiting** — 5

```promql
num_requests_waiting
```

**request_success_total** — 5

```promql
rate(request_success_total[2m])
```

**request_failure_total** — 5

```promql
rate(request_failure_total[2m])
```

**generation_tokens_total** — 5

```promql
rate(generation_tokens_total[2m])
```

**time_to_first_token_seconds** — 5

```promql
histogram_quantile(0.95, sum by (le) (rate(time_to_first_token_seconds_bucket[2m])))
```

**time_per_output_token_seconds** — 5

```promql
histogram_quantile(0.95, sum by (le) (rate(time_per_output_token_seconds_bucket[2m])))
```

**e2e_request_latency_seconds** — 5

```promql
histogram_quantile(0.95, sum by (le) (rate(e2e_request_latency_seconds_bucket[2m])))
```

</details>

## NIM Operator

Domain: inference. [Original documentation](https://docs.nvidia.com/nim-operator/latest/observability.html). Demo endpoint: `/metrics/nim_operator`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `nimCache_status_total` | gauge / resources | NIM cache resources by state. Inspect resource status and reconciliation. | `nimCache_status_total`; documented exporter name | [docs](https://docs.nvidia.com/nim-operator/latest/observability.html) |
| `nimService_status_total` | gauge / resources | NIM services by state. Inspect resource status and reconciliation. | `nimService_status_total`; documented exporter name | [docs](https://docs.nvidia.com/nim-operator/latest/observability.html) |
| `nimPipeline_status_total` | gauge / resources | NIM pipelines by state. Inspect resource status and reconciliation. | `nimPipeline_status_total`; documented exporter name | [docs](https://docs.nvidia.com/nim-operator/latest/observability.html) |
| `controller_runtime_reconcile_errors_total` | counter / errors | Controller reconciliation failures. Inspect operator logs. | `controller_runtime_reconcile_errors_total`; documented exporter name | [docs](https://docs.nvidia.com/nim-operator/latest/observability.html) |

<details><summary>Queries and cadence notes</summary>

**nimCache_status_total** — 5

```promql
nimCache_status_total
```

**nimService_status_total** — 5

```promql
nimService_status_total
```

**nimPipeline_status_total** — 5

```promql
nimPipeline_status_total
```

**controller_runtime_reconcile_errors_total** — 5

```promql
rate(controller_runtime_reconcile_errors_total[2m])
```

</details>

## Mission Control

Domain: operations. [Original documentation](https://docs.nvidia.com/dgx-superpod/reference-architecture-scalable-infrastructure-gb200/latest/dgx-software.html). Demo endpoint: `/metrics/mission_control`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_mission_control_recovery_active` | gauge / boolean | Lab model of a recovery workflow. Review diagnostics and proposed recovery; no hardware action is executed. | `Mission Control recovery workflow; not a published exporter metric`; lab-defined normalized metric | [docs](https://docs.nvidia.com/dgx-superpod/reference-architecture-scalable-infrastructure-gb200/latest/dgx-software.html) |

<details><summary>Queries and cadence notes</summary>

**lab_mission_control_recovery_active** — 5

```promql
lab_mission_control_recovery_active
```

</details>

## Application instrumentation

Domain: workload. [Original documentation](https://docs.pytorch.org/docs/stable/distributed.html). Demo endpoint: `/metrics/workload`.

| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |
|---|---|---|---|---|
| `lab_training_step_seconds` | gauge / second | Most recent training step per rank. Compare the slowest rank to the healthy baseline. | `Lab application instrumentation; not a vendor metric`; lab-defined normalized metric | [docs](https://docs.pytorch.org/docs/stable/distributed.html) |
| `lab_nccl_collective_seconds` | gauge / second | Most recent collective duration per rank. Compare the slowest rank to the healthy baseline. | `Lab application instrumentation; not a vendor metric`; lab-defined normalized metric | [docs](https://docs.pytorch.org/docs/stable/distributed.html) |
| `lab_training_tokens_total` | counter / tokens | Training tokens processed. Compare the slowest rank to the healthy baseline. | `Lab application instrumentation; not a vendor metric`; lab-defined normalized metric | [docs](https://docs.pytorch.org/docs/stable/distributed.html) |
| `lab_training_baseline_tokens_per_second` | gauge / tokens/s | Healthy throughput reference for a fixed workload. Compare the slowest rank to the healthy baseline. | `Lab application instrumentation; not a vendor metric`; lab-defined normalized metric | [docs](https://docs.pytorch.org/docs/stable/distributed.html) |
| `lab_capacity_lost_gpu_hours_total` | counter / GPU-hour equivalent | Integrated baseline-relative lost capacity estimate. Compare the slowest rank to the healthy baseline. | `Lab application instrumentation; not a vendor metric`; lab-defined normalized metric | [docs](https://docs.pytorch.org/docs/stable/distributed.html) |

<details><summary>Queries and cadence notes</summary>

**lab_training_step_seconds** — 5

```promql
lab_training_step_seconds
```

**lab_nccl_collective_seconds** — 5

```promql
lab_nccl_collective_seconds
```

**lab_training_tokens_total** — 5

```promql
rate(lab_training_tokens_total[2m])
```

**lab_training_baseline_tokens_per_second** — 5

```promql
lab_training_baseline_tokens_per_second
```

**lab_capacity_lost_gpu_hours_total** — 5

```promql
rate(lab_capacity_lost_gpu_hours_total[2m])
```

</details>
