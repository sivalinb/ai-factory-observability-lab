"""A source-linked, machine-readable contract; lab_* names are our own schema."""
import json
from pathlib import Path

ARTICLE = "https://developer.nvidia.com/blog/how-to-choose-full-stack-observability-for-nvidia-ai-factories/"
SOURCES = {
    "redfish": ("Redfish", "platform", "https://redfish.dmtf.org/redfish/schema_index"),
    "ipmi": ("IPMI Exporter", "platform", "https://github.com/prometheus-community/ipmi_exporter"),
    "dcgm": ("DCGM Exporter", "gpu", "https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html"),
    "nvsm": ("NVIDIA System Management", "platform", "https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/introduction.html"),
    "ufm": ("UFM Telemetry", "infiniband", "https://networking-docs.nvidia.com/ufmtelemetryum/1212/prometheus-endpoint-support"),
    "netq": ("NetQ Ethernet / RoCE", "ethernet", "https://docs.nvidia.com/networking-ethernet-software/cumulus-netq-51/Manage-Events-and-Notifications/TCA-Events-Reference/"),
    "nmx": ("NMX / NetQ NVLink", "nvlink", "https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html"),
    "bcm": ("Base Command Manager", "scheduling", "https://docs.nvidia.com/base-command-manager/"),
    "slurm": ("Slurm", "scheduling", "https://slurm.schedmd.com/squeue.html"),
    "runai": ("NVIDIA Run:ai", "scheduling", "https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/monitor-performance/metrics"),
    "nim": ("NVIDIA NIM", "inference", "https://docs.nvidia.com/nim/large-language-models/1.15.0/observability.html"),
    "nim_operator": ("NIM Operator", "inference", "https://docs.nvidia.com/nim-operator/latest/observability.html"),
    "mission_control": ("Mission Control", "operations", "https://docs.nvidia.com/dgx-superpod/reference-architecture-scalable-infrastructure-gb200/latest/dgx-software.html"),
    "workload": ("Application instrumentation", "workload", "https://docs.pytorch.org/docs/stable/distributed.html"),
}
SIGNALS = []


def signal(source, name, kind, unit, meaning, action, original=None, native=False,
           url=None, cadence=5, query=None):
    SIGNALS.append({
        "source": source, "name": name, "type": kind, "unit": unit,
        "meaning": meaning, "action": action, "original_field": original or name,
        "naming": "documented exporter name" if native else "lab-defined normalized metric",
        "source_url": url or SOURCES[source][2], "article_url": ARTICLE,
        "demo_cadence_seconds": 1, "suggested_scrape_seconds": 5,
        "upstream_cadence_note": cadence,
        "query": query or (f'rate({name}[2m])' if kind == "counter" else name),
    })


signal("redfish", "lab_redfish_fan_rpm", "gauge", "rpm", "Chassis fan rotation.", "Inspect cooling and fan status.", "Fan.Reading / Sensor.Reading; SPD_FAN_* sensor labels")
signal("redfish", "lab_redfish_psu_healthy", "gauge", "boolean", "Power supply health: 1 healthy, 0 fault.", "Inspect the power supply and redundancy.", "PowerSupply.Status.Health; PWR_* sensor labels")
signal("redfish", "lab_redfish_temperature_celsius", "gauge", "celsius", "Chassis sensor temperature.", "Check airflow and thermal limits.", "Sensor.Reading / Temperature.ReadingCelsius; TEMP_* sensor labels")
signal("redfish", "lab_redfish_bmc_healthy", "gauge", "boolean", "BMC manager health.", "Investigate management-plane availability.", "Manager.Status.Health")
for name, unit, meaning, original in [
    ("ipmi_fan_speed_rpm", "rpm", "Fan sensor reading.", "SPD_FAN_*"),
    ("ipmi_temperature_celsius", "celsius", "Temperature sensor reading.", "TEMP_*"),
    ("ipmi_sensor_state", "enum", "IPMI sensor severity; demo 0 nominal, 1 warning, 2 critical.", "PWR_*"),
]:
    signal("ipmi", name, "gauge", unit, meaning, "Inspect sensor and BMC event log.", original, native=True)
for name, kind, unit, meaning, action in [
    ("DCGM_FI_DEV_GPU_UTIL", "gauge", "percent", "GPU activity percentage.", "Compare to workload progress."),
    ("DCGM_FI_DEV_MEM_COPY_UTIL", "gauge", "percent", "Memory activity percentage.", "Check memory pressure."),
    ("DCGM_FI_DEV_POWER_USAGE", "gauge", "watt", "GPU board power draw.", "Compare to temperature and clocks."),
    ("DCGM_FI_DEV_GPU_TEMP", "gauge", "celsius", "GPU temperature.", "Inspect thermal throttling."),
    ("DCGM_FI_DEV_XID_ERRORS", "gauge", "error code", "Last observed XID code; not an event count.", "Classify XID and investigate the node."),
    ("DCGM_FI_DEV_ECC_DBE_VOL_TOTAL", "counter", "errors", "Volatile uncorrectable ECC count.", "Investigate GPU memory health."),
    ("DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL", "gauge", "MB/s (legacy)", "Legacy aggregate node NVLink throughput.", "Use the native byte/s field for base-unit analysis."),
    ("DCGM_FI_DEV_SM_CLOCK", "gauge", "MHz", "Streaming multiprocessor clock.", "Check clock limiting."),
    ("DCGM_FI_DEV_FB_USED", "gauge", "MiB", "Allocated framebuffer memory.", "Inspect memory headroom."),
    ("DCGM_FI_DEV_THERMAL_VIOLATION", "counter", "nanosecond", "Accumulated thermal limiting duration.", "Investigate cooling."),
]:
    signal("dcgm", name, kind, unit, meaning, action, native=True)
for field, meaning in [("system", "Overall DGX status."), ("storage", "Local drive/volume health."), ("cpu", "CPU health."), ("memory", "DIMM health."), ("pcie", "PCIe health.")]:
    signal("nvsm", f"lab_nvsm_{field}_healthy", "gauge", "boolean", meaning + " 1 healthy, 0 fault.", "Run NVSM health inspection.", f"NVSM {field} health; map the installed release")
UFM_HIGH = "https://networking-docs.nvidia.com/ufmenterpriseum/6244/high-frequency-primary-telemetry-fields"
UFM_LOW = "https://networking-docs.nvidia.com/ufmenterpriseum/6244/low-frequency-secondary-telemetry-fields"
for name, kind, unit, meaning, original, url, cadence in [
    ("lab_ufm_port_xmit_bytes_total", "counter", "byte", "Lab-integrated transmitted traffic in bytes.", "PortXmitDataExtended", UFM_HIGH, "UFM 6.24.4 describes sample-period bytes/data rate, not this cumulative lab counter. Integrate a validated rate; do not apply rate() to interval bytes."),
    ("lab_ufm_symbol_errors_total", "counter", "errors", "Accumulated symbol errors.", "SymbolErrorCounterExtended", UFM_HIGH, "Use a rate; allow counter resets."),
    ("lab_ufm_effective_ber_ratio", "gauge", "ratio", "Post-FEC bit error ratio.", "Effective_BER", UFM_LOW, "Some UFM releases collect secondary fields every 300 seconds."),
    ("lab_ufm_raw_ber_ratio", "gauge", "ratio", "Pre-FEC bit error ratio.", "Total_Raw_BER", UFM_LOW, "Pre-FEC errors alone do not establish workload impact."),
    ("lab_ufm_chip_temperature_celsius", "gauge", "celsius", "Switch chip temperature.", "Chip_Temp", UFM_LOW, "UFM 6.24.4 lists this as secondary telemetry; validate its collection cadence."),
    ("lab_ufm_congestion_wait_seconds_total", "counter", "second", "Lab-integrated transmit-wait duration.", "PortXmitWaitExtended; requires device-specific conversion", UFM_HIGH, "Sample-window ticks require conversion and accumulation using the installed device documentation."),
]:
    signal("ufm", name, kind, unit, meaning, "Inspect affected link in UFM; correlate to ranks.", original, url=url, cadence=cadence)
for name, kind, unit, meaning, original in [
    ("lab_netq_pfc_pause_seconds_total", "counter", "second", "Normalized PFC pause time.", "Rx RoCE PFC pause duration"),
    ("lab_netq_ecn_marked_packets_total", "counter", "packets", "ECN-marked traffic.", "Tx ECN marked packets"),
    ("lab_netq_dropped_packets_total", "counter", "packets", "Congestion-related drops.", "Rx RoCE no buffer discard"),
    ("lab_netq_link_flaps_total", "counter", "events", "Link state transitions.", "Link flap errors"),
    ("lab_netq_buffer_usage_ratio", "gauge", "ratio", "Normalized RoCE buffer occupancy.", "Rx RoCE buffer usage"),
]:
    signal("netq", name, kind, unit, meaning, "Inspect RoCE QoS, buffers and affected interface.", original)
for name, kind, unit, meaning, original in [
    ("lab_nmx_link_healthy", "gauge", "boolean", "NVLink link health.", "NVLink link status; installed schema"),
    ("lab_nmx_link_bytes_total", "counter", "byte", "Normalized NVLink traffic.", "NVLink throughput; installed schema"),
    ("lab_nmx_link_errors_total", "counter", "errors", "Normalized NVLink errors.", "NVLink errors; installed schema"),
    ("lab_nmx_partition_healthy", "gauge", "boolean", "NVLink partition health.", "NVLink partition Health"),
]:
    signal("nmx", name, kind, unit, meaning, "Inspect NVSwitch domain and partition.", original)
for source, fields in {
    "bcm": [("running_jobs", "jobs", "Running job count."), ("reserved_gpus", "GPUs", "Reserved GPU count."), ("queue_wait_seconds", "second", "Oldest pending job wait."), ("idle_allocated_gpus", "GPUs", "Allocated GPUs lacking useful progress."), ("node_healthy", "boolean", "Managed node health.")],
    "slurm": [("running_jobs", "jobs", "Running Slurm jobs."), ("queue_wait_seconds", "second", "Oldest pending Slurm job wait.")],
    "runai": [("allocated_gpus", "GPUs", "Project GPU allocation."), ("quota_gpus", "GPUs", "Project guaranteed quota."), ("pending_jobs", "jobs", "Pending workload count."), ("queue_wait_seconds", "second", "Oldest pending workload wait."), ("idle_allocated_gpus", "GPUs", "Allocated GPUs without useful progress.")],
}.items():
    for field, unit, meaning in fields:
        signal(source, f"lab_{source}_{field}", "gauge", unit, meaning, "Inspect placement, reservations and quota policy.", f"{source} API/exporter concept; explicit installation mapping required")
for name, kind, unit, meaning in [
    ("gpu_cache_usage_perc", "gauge", "ratio", "GPU KV-cache occupancy, from 0 to 1."),
    ("num_requests_running", "gauge", "requests", "Executing inference requests."),
    ("num_requests_waiting", "gauge", "requests", "Queued inference requests."),
    ("request_success_total", "counter", "requests", "Successful model generations."),
    ("request_failure_total", "counter", "requests", "Failed model generations."),
    ("generation_tokens_total", "counter", "tokens", "Generated output tokens."),
    ("time_to_first_token_seconds", "histogram", "second", "First-token latency distribution."),
    ("time_per_output_token_seconds", "histogram", "second", "Output-token latency distribution."),
    ("e2e_request_latency_seconds", "histogram", "second", "Request completion latency distribution."),
]:
    query = f'histogram_quantile(0.95, sum by (le) (rate({name}_bucket[2m])))' if kind == "histogram" else None
    signal("nim", name, kind, unit, meaning, "Compare demand, queueing and cache pressure.", native=True, query=query)
for name, meaning in [("nimCache_status_total", "NIM cache resources by state."), ("nimService_status_total", "NIM services by state."), ("nimPipeline_status_total", "NIM pipelines by state.")]:
    signal("nim_operator", name, "gauge", "resources", meaning, "Inspect resource status and reconciliation.", native=True)
signal("nim_operator", "controller_runtime_reconcile_errors_total", "counter", "errors", "Controller reconciliation failures.", "Inspect operator logs.", native=True)
signal("mission_control", "lab_mission_control_recovery_active", "gauge", "boolean", "Lab model of a recovery workflow.", "Review diagnostics and proposed recovery; no hardware action is executed.", "Mission Control recovery workflow; not a published exporter metric")
for name, kind, unit, meaning in [
    ("lab_training_step_seconds", "gauge", "second", "Most recent training step per rank."),
    ("lab_nccl_collective_seconds", "gauge", "second", "Most recent collective duration per rank."),
    ("lab_training_tokens_total", "counter", "tokens", "Training tokens processed."),
    ("lab_training_baseline_tokens_per_second", "gauge", "tokens/s", "Healthy throughput reference for a fixed workload."),
    ("lab_capacity_lost_gpu_hours_total", "counter", "GPU-hour equivalent", "Integrated baseline-relative lost capacity estimate."),
]:
    signal("workload", name, kind, unit, meaning, "Compare the slowest rank to the healthy baseline.", "Lab application instrumentation; not a vendor metric")


def export_catalog(root):
    root = Path(root)
    data = {"schema_version": 1, "article_url": ARTICLE, "sources": {
        k: {"title": v[0], "domain": v[1], "documentation_url": v[2],
            "demo_mode": "simulated", "endpoint": f"/metrics/{k}"}
        for k, v in SOURCES.items()}, "signals": SIGNALS}
    (root / "catalog/signals.json").write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Signal atlas", "", "Generated from `lab/catalog.py`. Every default feed is simulated. `lab_*` names are project normalization contracts, not claims about vendor exporter names.", "", f"Framework: [original NVIDIA article]({ARTICLE}).", "", "Native metric names are version-specific. Inspect the actual exporter output and apply explicit mappings. BMC wildcards in the article describe sensor labels, not universal Prometheus metric names.", ""]
    for source, (title, domain, url) in SOURCES.items():
        lines += [f"## {title}", "", f"Domain: {domain}. [Original documentation]({url}). Demo endpoint: `/metrics/{source}`.", "", "| Signal | Type / unit | Meaning and interpretation | Original field / naming | Source |", "|---|---|---|---|---|"]
        for s in (x for x in SIGNALS if x["source"] == source):
            lines.append(f'| `{s["name"]}` | {s["type"]} / {s["unit"]} | {s["meaning"]} {s["action"]} | `{s["original_field"]}`; {s["naming"]} | [docs]({s["source_url"]}) |')
        lines += ["", "<details><summary>Queries and cadence notes</summary>", ""]
        for s in (x for x in SIGNALS if x["source"] == source):
            lines += [f'**{s["name"]}** — {s["upstream_cadence_note"]}', "", "```promql", s["query"], "```", ""]
        lines += ["</details>", ""]
    (root / "docs/signals.md").write_text("\n".join(lines))


if __name__ == "__main__":
    export_catalog(Path(__file__).resolve().parents[1])
