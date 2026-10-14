# Native integrations

Default feeds are simulated; the project does not provision a cloud account or install proprietary NVIDIA products. A source can use `simulated`, `prometheus`, `json` or `redfish` mode. Sources absent from the configuration retain simulated mode.

## Cloud GPU path

1. Use a Linux NVIDIA GPU host with the appropriate driver/runtime. Follow the [official DCGM Exporter installation guide](https://docs.nvidia.com/datacenter/dcgm/latest/installation/install-dcgm-exporter.html) and its paired DCGM compatibility guidance.
2. Verify the actual `/metrics` output on port 9400. A selected field can still be unsupported on the instance. Unsupported integer DCGM sentinel values are omitted by this adapter rather than interpreted as hardware readings.
3. Deploy a compatible NIM image/profile using [NIM deployment documentation](https://docs.nvidia.com/nim/large-language-models/2.0.11/deployment/kubernetes-deployment/nim-operator-deployment.html). Image/model access, GPU memory and metric names depend on the deployment. Check the real metrics path; `/v1/metrics` is the documented path for the legacy NIM version modeled here.
4. Reach the remote exporters through a private connection or your normal tunnel. Configure the local adapter URLs and verified node labels. No cloud spending or remote provisioning is performed by this repository.
5. Start the optional `workloads/train.py` application and connect its measured endpoint as the `workload` feed if desired.

```json
{
  "dcgm": {
    "mode": "prometheus",
    "url": "http://127.0.0.1:9400/metrics",
    "labels": {"node": "gpu-host"},
    "label_map": {"Hostname": "node", "hostname": "node"}
  },
  "nim": {
    "mode": "prometheus",
    "url": "http://127.0.0.1:8000/v1/metrics",
    "labels": {"node": "gpu-host"}
  },
  "workload": {
    "mode": "prometheus",
    "url": "http://127.0.0.1:8091/metrics"
  }
}
```

For containers, localhost is the container itself; use an appropriate internal hostname or tunnel endpoint. Mount the ignored source configuration into the lab service and set `LAB_SOURCES_CONFIG` to that path. A sample Compose override is below; endpoint addressing must suit your environment.

```yaml
services:
  lab:
    environment:
      LAB_SOURCES_CONFIG: /app/config/sources.local.json
    volumes:
      - ./config/sources.local.json:/app/config/sources.local.json:ro
```

## Prometheus adapter for every exporter source

NVSM, UFM, NMX, BCM, Slurm, Run:ai, NIM Operator and IPMI can use the same implemented transport when a suitable Prometheus endpoint exists. Enter the endpoint supplied by the installed product, and use `rename`, `scale` and `label_map` only after inspecting that endpoint. Examples below are **configuration contracts**, not claims about product default paths or schemas.

```json
{
  "ufm": {
    "mode": "prometheus",
    "url": "https://YOUR_VERIFIED_UFM_ENDPOINT/metrics",
    "token_env": "UFM_API_TOKEN",
    "labels": {"node": "VERIFIED_PORT_PEER_NODE"},
    "rename": {"YOUR_EFFECTIVE_BER_METRIC": "lab_ufm_effective_ber_ratio"}
  }
}
```

`token_env`, `username_env` and `password_env` reference local environment variables. `ca_file` accepts a trusted CA bundle for private PKI. TLS verification is enabled. Credentials are not embedded in the source examples or dashboard metadata.

Histogram renaming preserves `_bucket`, `_sum`, `_count`, and `le`. Newer NIM backends may use different metric families; map the actual exported names to the catalog before using its queries. Validate outcome semantics too: successful model generation is distinct from an HTTP gateway success measurement.

## Explicit JSON normalization

Use installed product APIs where Prometheus exposition is unavailable. The mapper supports JSON pointers, arrays, numeric scaling, state mappings and label extraction. The following demonstrates the mapper against a hypothetical `ports` response; it is deliberately **not** presented as a NetQ or UFM native JSON schema.

```json
{
  "netq": {
    "mode": "json",
    "url": "https://YOUR_VERIFIED_API_ENDPOINT",
    "token_env": "NETWORK_API_TOKEN",
    "mappings": [
      {
        "metric": "lab_netq_buffer_usage_ratio",
        "records_pointer": "/ports",
        "value_pointer": "/buffer_percent",
        "scale": 0.01,
        "label_pointers": {"node": "/peer_node", "port": "/name"}
      }
    ]
  }
}
```

UFM's current `PortXmitDataExtended` documentation describes data rate/sample-period bytes. The lab's `lab_ufm_port_xmit_bytes_total` is an **integrated cumulative counter**. If your input is already a validated bytes/s rate, map it and set `counter_from_rate: true` on the JSON mapping, or list the mapped name in the Prometheus adapter's `counter_from_rate` array. The adapter integrates held-sample rate over elapsed collection time. If the input is interval bytes, first divide by its validated measurement interval. If it is a cumulative hardware counter, use its correct units directly. Do not call `rate()` on a per-interval byte quantity.

Integration state is process-local and resets on restart; Prometheus counter-reset handling applies. It is an estimate from sampled rates, not exact hardware accounting. Transmit-wait ticks require device-specific conversion to seconds before accumulation.

## Redfish and IPMI

The implemented Redfish adapter reads legacy Thermal/Power resources and modern Sensor/PowerSupply/Manager instances. Supply verified paths; it does not guess a BMC's resource IDs or traverse every resource automatically. See the [DMTF schema index](https://redfish.dmtf.org/redfish/schema_index).

`config/sources.example.json` includes a Redfish configuration. The IPMI path uses a separately deployed [IPMI Exporter](https://github.com/prometheus-community/ipmi_exporter). The lab does not execute `ipmitool` or issue BMC control commands. Select one authoritative production source for overlapping BMC measurements.

## Cadence, aliases and data meaning

- UFM 6.24.4 documents default **30-second primary** and **300-second secondary** collection periods. A 5-second scrape cannot improve those upstream periods. [Primary fields](https://networking-docs.nvidia.com/ufmenterpriseum/6244/high-frequency-primary-telemetry-fields), [secondary fields](https://networking-docs.nvidia.com/ufmenterpriseum/6244/low-frequency-secondary-telemetry-fields).
- `DCGM_FI_DEV_XID_ERRORS` is an error-code gauge. It is not an event counter and does not establish event freshness by itself.
- The legacy DCGM NVLink field modeled here reports **MB/s**; native base-unit throughput fields have different conversion semantics. Thermal-violation legacy fields report nanoseconds. Check the [DCGM field reference](https://docs.nvidia.com/datacenter/dcgm/latest/reference/field-identifiers.html).
- GPU utilization aliases can differ in percent/ratio semantics by field ID and exporter release. Configure scaling after checking the actual field binding.
- NIM Operator resource metrics ending in `_total` can be **gauges**. Metric suffixes alone do not establish type.
- Native NMX management is documented as **NetQ NVLink**, formerly NMX-M; NMX-T and NMX-C retain separate roles. [Original documentation](https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.1.0/nvlink-management-software.html).
- The sample lab thresholds express controlled experiments, not vendor BER, thermal or inference limits.

## Deployment-specific work remaining for enterprise use

The generic adapters are implemented and tested. Each proprietary product still needs access, an installed-release mapping and validation against its real endpoint. Actual GPU/job/fabric topology discovery, multi-cluster tenancy, production authentication, long-term retention, high availability, cardinality limits and automated hardware remediation are outside this laptop lab. gNMI/SNMP can feed a dedicated collector that exposes Prometheus or the explicit JSON contract; no native gNMI/SNMP client is bundled.
