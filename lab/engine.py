"""Deterministic synthetic factory, with counter integration and evidence-based triage."""
import math
import time
from collections import defaultdict
from .catalog import SOURCES
from .metrics import Sample

NODES = ("dgx-01", "dgx-02", "eth-01", "nvl-01")
SCENARIOS = {
    "normal": ("Healthy baseline", "All synthetic domains are nominal."),
    "ib_gray_failure": ("InfiniBand gray failure", "BER and symbol errors rise while GPU utilization stays high."),
    "gpu_xid": ("GPU XID event", "GPU-03 reports XID 48 and uncorrectable ECC events."),
    "thermal": ("Cooling degradation", "Fan and PSU faults coincide with hot GPUs and clock limiting."),
    "roce_congestion": ("RoCE congestion", "PFC pauses, ECN and drops coincide with inference delays."),
    "nvlink_degradation": ("Rack NVLink degradation", "A rack link and partition degrade while collectives slow."),
    "scheduler_starvation": ("Scheduling starvation", "Pending jobs wait while allocated GPUs remain idle."),
    "inference_overload": ("Inference overload", "Request demand exceeds service capacity and fills the KV cache."),
    "storage_stall": ("Local storage degradation", "DGX storage health and input progress degrade."),
    "telemetry_gap": ("Telemetry gap", "The UFM feed is unavailable; it must not look healthy."),
}
DOMAINS = {
    "platform": "PLATFORM", "gpu": "GPU COMPUTE", "infiniband": "INFINIBAND",
    "ethernet": "ETHERNET / RoCE", "nvlink": "RACK NVLINK", "scheduling": "SCHEDULING", "inference": "INFERENCE",
}


class Simulator:
    def __init__(self, now=None):
        self.last_tick = float(now if now is not None else time.time())
        self.scenario = "normal"
        self.counters = defaultdict(float)
        self.samples = {}
        self.update(self.last_tick)

    def set_scenario(self, name):
        if name not in SCENARIOS:
            raise ValueError("Unknown scenario")
        self.scenario = name

    def update(self, now=None):
        now = float(now if now is not None else time.time())
        dt = max(0, now - self.last_tick)
        self.last_tick = now
        result = {key: [] for key in SOURCES}
        f = self.scenario
        wave = math.sin(now / 11)

        def add(source, metric, value, **labels):
            labels = {"cluster": "factory-lab", "origin": "simulated", "source": source, **labels}
            result[source].append(Sample(metric, float(value), labels))

        def counter(source, name, rate, **labels):
            key = (source, name, tuple(sorted(labels.items())))
            self.counters[key] += max(0, rate) * dt
            add(source, name, self.counters[key], **labels)

        for i, node in enumerate(NODES):
            hot = f == "thermal" and node == "dgx-02"
            temp = 88 + wave if hot else 46 + i * 3 + wave
            add("redfish", "lab_redfish_fan_rpm", 700 if hot else 7200 + 220 * wave, node=node, sensor="SPD_FAN_FAN1")
            add("redfish", "lab_redfish_psu_healthy", 0 if hot else 1, node=node, sensor="PWR_PSU1")
            add("redfish", "lab_redfish_temperature_celsius", temp, node=node, sensor="TEMP_INLET")
            add("redfish", "lab_redfish_bmc_healthy", 1, node=node)
            add("ipmi", "ipmi_fan_speed_rpm", 700 if hot else 7200 + 220 * wave, node=node, name="SPD_FAN_FAN1", id="1")
            add("ipmi", "ipmi_temperature_celsius", temp, node=node, name="TEMP_INLET", id="2")
            add("ipmi", "ipmi_sensor_state", 2 if hot else 0, node=node, name="PWR_PSU1", type="Power Supply", id="3")
            for gpu in range(2):
                broken = f == "gpu_xid" and i == 1 and gpu == 1
                idle = f == "scheduler_starvation" and i >= 2
                labels = {"node": node, "gpu": str(gpu), "UUID": f"GPU-{i * 2 + gpu:02d}"}
                add("dcgm", "DCGM_FI_DEV_GPU_UTIL", 2 if broken or idle else 72 + i * 3 + gpu * 2 + wave * 5, **labels)
                add("dcgm", "DCGM_FI_DEV_MEM_COPY_UTIL", 28 + i * 6 + wave * 5, **labels)
                add("dcgm", "DCGM_FI_DEV_POWER_USAGE", 110 if broken or idle else 330 + i * 14 + wave * 18, **labels)
                add("dcgm", "DCGM_FI_DEV_GPU_TEMP", 91 + wave if hot else 61 + i * 2 + gpu * 3 + wave * 3, **labels)
                add("dcgm", "DCGM_FI_DEV_XID_ERRORS", 48 if broken else 0, **labels)
                counter("dcgm", "DCGM_FI_DEV_ECC_DBE_VOL_TOTAL", 0.25 if broken else 0, **labels)
                add("dcgm", "DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL", 60000 + 4000 * wave if i < 2 else 0, **labels)
                add("dcgm", "DCGM_FI_DEV_SM_CLOCK", 810 if hot else 1680 + wave * 30, **labels)
                add("dcgm", "DCGM_FI_DEV_FB_USED", 31000 + i * 2500, **labels)
                counter("dcgm", "DCGM_FI_DEV_THERMAL_VIOLATION", 1e9 if hot else 0, **labels)
            if i < 2:
                for part in ("system", "storage", "cpu", "memory", "pcie"):
                    bad = node == "dgx-02" and ((part == "storage" and f == "storage_stall") or (part == "system" and f in ("thermal", "storage_stall", "gpu_xid")))
                    add("nvsm", f"lab_nvsm_{part}_healthy", 0 if bad else 1, node=node)
            add("bcm", "lab_bcm_node_healthy", 0 if node == "dgx-02" and f in ("gpu_xid", "thermal", "storage_stall") else 1, node=node)

        for i in range(4):
            impaired = f == "ib_gray_failure" and i == 3
            port = str(17 + i)
            node = "dgx-01" if i < 2 else "dgx-02"
            labels = {"switch": "ib-leaf-01", "port": port, "node": node}
            counter("ufm", "lab_ufm_port_xmit_bytes_total", 7e9 + i * 1e9 + wave * 2e8, **labels)
            counter("ufm", "lab_ufm_symbol_errors_total", 28 if impaired else 0, **labels)
            add("ufm", "lab_ufm_effective_ber_ratio", 8e-9 if impaired else 2e-15, **labels)
            add("ufm", "lab_ufm_raw_ber_ratio", 2e-5 if impaired else 1e-9, **labels)
            add("ufm", "lab_ufm_chip_temperature_celsius", 55 + wave, **labels)
            counter("ufm", "lab_ufm_congestion_wait_seconds_total", 0.24 if impaired else 0.003, **labels)
        if f == "telemetry_gap":
            result["ufm"] = []

        congested = f == "roce_congestion"
        net_labels = {"switch": "spectrum-01", "port": "swp8", "node": "eth-01"}
        counter("netq", "lab_netq_pfc_pause_seconds_total", 0.3 if congested else 0.002, **net_labels)
        counter("netq", "lab_netq_ecn_marked_packets_total", 800 if congested else 2, **net_labels)
        counter("netq", "lab_netq_dropped_packets_total", 60 if congested else 0, **net_labels)
        counter("netq", "lab_netq_link_flaps_total", 0, **net_labels)
        add("netq", "lab_netq_buffer_usage_ratio", 0.95 if congested else 0.24 + wave * 0.04, **net_labels)
        nvl_bad = f == "nvlink_degradation"
        nvl_labels = {"rack": "nvl-rack-01", "node": "nvl-01", "link": "nvl-7", "partition": "p0"}
        add("nmx", "lab_nmx_link_healthy", 0 if nvl_bad else 1, **nvl_labels)
        counter("nmx", "lab_nmx_link_bytes_total", 10e9 if nvl_bad else 50e9 + wave * 2e9, **nvl_labels)
        counter("nmx", "lab_nmx_link_errors_total", 12 if nvl_bad else 0, **nvl_labels)
        add("nmx", "lab_nmx_partition_healthy", 0 if nvl_bad else 1, **nvl_labels)

        starved = f == "scheduler_starvation"
        add("bcm", "lab_bcm_running_jobs", 3)
        add("bcm", "lab_bcm_reserved_gpus", 8)
        add("bcm", "lab_bcm_queue_wait_seconds", 600 if starved else 12 + wave * 3)
        add("bcm", "lab_bcm_idle_allocated_gpus", 4 if starved else 0)
        add("slurm", "lab_slurm_running_jobs", 1, partition="training")
        add("slurm", "lab_slurm_queue_wait_seconds", 30, partition="training")
        for project, allocation in [("research", 2), ("serving", 2)]:
            add("runai", "lab_runai_allocated_gpus", allocation, project=project)
            add("runai", "lab_runai_quota_gpus", 2, project=project)
            add("runai", "lab_runai_pending_jobs", 6 if starved else 0, project=project)
            add("runai", "lab_runai_queue_wait_seconds", 600 if starved else 8, project=project)
            add("runai", "lab_runai_idle_allocated_gpus", 2 if starved else 0, project=project)

        overloaded = f == "inference_overload"
        slow_inference = overloaded or congested
        infer_labels = {"model": "demo-llm", "node": "eth-01", "service": "nim-chat"}
        add("nim", "gpu_cache_usage_perc", 0.97 if overloaded else 0.57 + wave * 0.08, **infer_labels)
        add("nim", "num_requests_running", 16 if overloaded else 4, **infer_labels)
        add("nim", "num_requests_waiting", 38 if slow_inference else 1, **infer_labels)
        request_rate = 5 + wave * 0.3
        fail_rate = 0.6 if overloaded else (0.15 if congested else 0.005)
        counter("nim", "request_success_total", request_rate - fail_rate, **infer_labels)
        counter("nim", "request_failure_total", fail_rate, **infer_labels)
        counter("nim", "generation_tokens_total", 420 if slow_inference else 1200 + wave * 50, **infer_labels)
        for metric, latency in [("time_to_first_token_seconds", 2.8 if slow_inference else 0.32), ("time_per_output_token_seconds", 0.12 if slow_inference else 0.025), ("e2e_request_latency_seconds", 8.0 if slow_inference else 1.2)]:
            bounds = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, math.inf)
            for bound in bounds:
                fraction = 1 if math.isinf(bound) else 1 - math.exp(-bound / latency)
                counter("nim", metric + "_bucket", request_rate * fraction, le="+Inf" if math.isinf(bound) else str(bound), **infer_labels)
            counter("nim", metric + "_count", request_rate, **infer_labels)
            counter("nim", metric + "_sum", request_rate * latency, **infer_labels)
        for metric in ("nimCache_status_total", "nimService_status_total", "nimPipeline_status_total"):
            add("nim_operator", metric, 1, state="Ready", namespace="inference")
        counter("nim_operator", "controller_runtime_reconcile_errors_total", 0, controller="nimservice")
        add("mission_control", "lab_mission_control_recovery_active", 1 if f in ("gpu_xid", "thermal", "storage_stall") else 0, node="dgx-02")

        slowdown = {"ib_gray_failure": 0.42, "gpu_xid": 0.65, "thermal": 0.35, "storage_stall": 0.45}.get(f, 0)
        for rank in range(4):
            add("workload", "lab_training_step_seconds", (0.16 + rank * 0.005 + wave * 0.005) / (1 - slowdown), workload="train-42", rank=str(rank), node="dgx-01" if rank < 2 else "dgx-02")
            add("workload", "lab_nccl_collective_seconds", 0.17 if f == "ib_gray_failure" and rank == 3 else (0.12 if f == "ib_gray_failure" else 0.022 + rank * 0.002), workload="train-42", rank=str(rank), node="dgx-01" if rank < 2 else "dgx-02")
        add("workload", "lab_training_baseline_tokens_per_second", 16000, workload="train-42")
        counter("workload", "lab_training_tokens_total", (16000 + wave * 160) * (1 - slowdown), workload="train-42")
        add("workload", "lab_training_step_seconds", 0.9 if nvl_bad else 0.19, workload="train-nvl", rank="0", node="nvl-01")
        add("workload", "lab_nccl_collective_seconds", 0.62 if nvl_bad else 0.028, workload="train-nvl", rank="0", node="nvl-01")
        lost_rate = (4 * slowdown + (2 * 0.7 if nvl_bad else 0)) / 3600
        counter("workload", "lab_capacity_lost_gpu_hours_total", lost_rate)
        self.samples = result
        return result


def diagnose(samples, source_up):
    """Observed evidence with node and origin joins; never inspect scenario names."""
    flat = [sample for group in samples.values() for sample in group]
    candidates = []
    def find(name, predicate):
        return [s for s in flat if s.name == name and predicate(s.value)]
    def related(cause, name, predicate):
        node, origin = cause.labels.get("node"), cause.labels.get("origin")
        if not node or not origin:
            return []
        return [s for s in find(name, predicate) if s.labels.get("node") == node and s.labels.get("origin") == origin]
    def placement(cause):
        jobs = related(cause, "lab_training_step_seconds", lambda x: True)
        return ", ".join(sorted({s.labels.get("workload", "unmapped") for s in jobs})) or cause.labels.get("service", "placement not mapped")
    def add(domain, title, evidence, action, cause=None, workload=None):
        node = cause.labels.get("node", "asset not mapped") if cause else "collector"
        origin = cause.labels.get("origin", "unknown") if cause else "derived"
        job = workload or (placement(cause) if cause else "coverage")
        item = {"domain": domain, "title": title, "evidence": evidence, "action": action,
                "node": node, "workload": job, "runbook": "/runbooks#" + domain,
                "confidence": "rule-supported hypothesis", "evidence_origin": origin}
        if not any((c["domain"], c["title"], c["node"]) == (domain, title, node) for c in candidates):
            candidates.append(item)
    down = [source for source, up in source_up.items() if not up]
    if down:
        add("telemetry", "Telemetry coverage gap", "Unavailable sources: " + ", ".join(down), "Restore collection before judging domain health.")
    for cause in find("DCGM_FI_DEV_XID_ERRORS", lambda x: x > 0):
        add("gpu", "GPU health event", "A nonzero XID code was observed on " + cause.labels.get("UUID", "an unmapped GPU") + ".", "Classify XID; inspect the affected node and actual job placement.", cause)
    for cause in find("lab_redfish_psu_healthy", lambda x: x < 1):
        if related(cause, "DCGM_FI_DEV_GPU_TEMP", lambda x: x > 85):
            add("platform", "Cooling or power degradation", "PSU fault and hot GPUs share the same node and telemetry origin.", "Inspect cooling and power; consider draining the affected node.", cause)
    for cause in find("lab_nvsm_storage_healthy", lambda x: x < 1):
        add("platform", "Local storage degradation", "NVSM storage health is unhealthy.", "Inspect volume/drive health and input pipeline progress.", cause)
    for cause in find("lab_ufm_effective_ber_ratio", lambda x: x > 1e-10):
        ranks = related(cause, "lab_nccl_collective_seconds", lambda x: x > .08)
        if ranks:
            port = cause.labels.get("switch", "unmapped switch") + "/" + cause.labels.get("port", "unmapped port")
            add("infiniband", "InfiniBand gray failure", "Effective BER and slow collectives share a node and origin.", "Inspect " + port + " and its cable in UFM.", cause, ", ".join(sorted({r.labels.get("workload", "unmapped") for r in ranks})))
    for cause in find("lab_netq_buffer_usage_ratio", lambda x: x > .85):
        if related(cause, "num_requests_waiting", lambda x: x > 10):
            add("ethernet", "RoCE congestion", "Buffer pressure and request queueing share the same node and origin.", "Inspect the affected RoCE interface, PFC, ECN and drops.", cause, "nim-chat" if cause.labels.get("origin") == "simulated" else "service placement requires mapping")
    for cause in find("lab_nmx_link_healthy", lambda x: x < 1):
        add("nvlink", "Rack NVLink degradation", "The NVLink link reports unhealthy state.", "Inspect rack " + cause.labels.get("rack", "unmapped") + " and link " + cause.labels.get("link", "unmapped") + ".", cause)
    for cause in find("lab_runai_queue_wait_seconds", lambda x: x > 120):
        idle = [s for s in find("lab_runai_idle_allocated_gpus", lambda x: x > 0) if s.labels.get("project") == cause.labels.get("project") and s.labels.get("origin") == cause.labels.get("origin")]
        if idle:
            add("scheduling", "Scheduling starvation", "Long waits and idle allocations share project " + cause.labels.get("project", "unmapped") + ".", "Review reservations, quota and placement policy.", cause, "pending workloads")
    for cause in find("gpu_cache_usage_perc", lambda x: x > .9):
        if related(cause, "num_requests_waiting", lambda x: x > 10):
            add("inference", "Inference capacity pressure", "KV-cache pressure coincides with queueing on the same node and origin.", "Review concurrency and token limits; benchmark added capacity.", cause)
    status = {domain: (2 if any(c["domain"] == domain for c in candidates) else 0) for domain in DOMAINS}
    for source in down:
        domain = SOURCES[source][1]
        if domain in status:
            status[domain] = 3
    return candidates, status
