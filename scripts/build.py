#!/usr/bin/env python3
"""Rebuild reproducible Grafana dashboards, configs and source-linked documentation."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.catalog import SOURCES, SIGNALS, export_catalog

DS = {"type": "prometheus", "uid": "factory-prometheus"}
PLUGIN = "marcusolsson-dynamictext-panel"
CSS = """
& { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #eef3ef; }
.hero {padding: 20px 24px; display:flex; justify-content:space-between; align-items:center; background:linear-gradient(110deg,#19261d,#121820 68%); border-left:4px solid #b7f77b; min-height:90px;}
.eyebrow {font-size:10px; font-weight:700; letter-spacing:2.3px; color:#b7f77b; margin-bottom:8px;}
.headline {font-size:27px; font-weight:600; letter-spacing:-0.7px; margin:0 0 6px;}
.subline {font-size:12px; color:#a3afa8; line-height:1.5;}
.pill {border:1px solid #5c6b43; border-radius:18px; padding:6px 12px; font-size:10px; letter-spacing:1px; color:#b7f77b; white-space:nowrap;}
.nav {display:flex;gap:14px;margin-top:13px;flex-wrap:wrap;}
.nav a,.runbook a {color:#c8ef99;text-decoration:none;font-size:11px;}
.domains {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;padding:12px 8px;}
.domain {background:#171f1c;border:1px solid #34413a;border-radius:7px;padding:14px 10px;min-height:78px;}
.domain-title {font-size:9px;letter-spacing:1.1px;color:#aab7ae;margin-bottom:14px;}
.status {font-size:12px;font-weight:600;letter-spacing:.4px;}
.caption {font-size:9px;color:#7f8b84;margin-top:9px;}
.brief {padding:17px 18px;border-left:3px solid #ff9770;background:linear-gradient(130deg,#251c18,#161b20);margin:8px;border-radius:3px;}
.brief h3 {font-size:18px;margin:9px 0 12px;letter-spacing:-.3px;}
.brief p {color:#c1c6c0;font-size:11px;line-height:1.65;margin:8px 0;}
.brief .meta {font-size:10px;color:#a9b8a9;letter-spacing:.3px;}
.runbook {margin-top:12px;border-top:1px solid #39413a;padding-top:10px;}
.source-grid {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;padding:8px;}
.source {padding:12px;background:#17201d;border:1px solid #34413a;border-radius:6px;}
.source b {font-size:12px;color:#d9eed0;} .source small {display:block;font-size:10px;color:#96a599;margin-top:7px;}
.source a {display:block;font-size:10px;color:#b7f77b;margin-top:8px;}
@media(max-width:900px){.domains{grid-template-columns:repeat(4,minmax(0,1fr));}.headline{font-size:22px}.source-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
"""


def target(expr, ref="A", table=False, instant=False, legend=""):
    return {"refId": ref, "expr": expr, "datasource": DS, "editorMode": "code", "format": "table" if table else "time_series", "instant": instant, "range": not instant, "legendFormat": legend}


def panel(kind, title, x, y, w, h, expr=None, unit="short", legend="", options=None, description="", targets=None, overrides=None):
    result = {"type": kind, "title": title, "gridPos": {"x": x, "y": y, "w": w, "h": h}, "datasource": DS,
              "description": description, "targets": targets or ([target(expr, legend=legend)] if expr else []),
              "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "palette-classic"}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 80}, {"color": "red", "value": 95}]}}, "overrides": overrides or []}, "options": options or {}}
    if kind == "timeseries":
        result["fieldConfig"]["defaults"]["custom"] = {"drawStyle": "line", "lineInterpolation": "smooth", "lineWidth": 2, "fillOpacity": 12, "showPoints": "never", "axisPlacement": "auto", "spanNulls": False}
        result["options"] = {"legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}, **(options or {})}
    elif kind == "stat":
        result["options"] = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "colorMode": "value", "graphMode": "area", "justifyMode": "auto", "orientation": "auto", "textMode": "auto", **(options or {})}
    elif kind in ("gauge", "bargauge"):
        result["options"] = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "orientation": "horizontal", "displayMode": "gradient", "showThresholdLabels": False, "showThresholdMarkers": True, **(options or {})}
    elif kind == "table":
        result["options"] = {"showHeader": True, "cellHeight": "sm", "sortBy": [], **(options or {})}
    return result


def business(title, x, y, w, h, expr, html, css=CSS):
    p = panel(PLUGIN, title, x, y, w, h, targets=[target(expr, table=True, instant=True)])
    p["options"] = {"content": html, "defaultContent": "<div class='brief'><h3>Telemetry unavailable</h3><p>Check the source feed and time range. Missing telemetry is not healthy telemetry.</p></div>", "renderMode": "allRows", "editors": ["styles"], "editor": {"language": "html", "format": "auto"}, "styles": css, "helpers": "", "afterRender": "", "externalStyles": [], "contentPartials": [], "wrap": False}
    return p


NAV = "<div class='nav'><a href='/d/factory-overview'>Overview ↗</a><a href='/d/factory-fabric'>Fabric ↗</a><a href='/d/factory-workloads'>Workloads ↗</a><a href='/d/factory-signals'>Signal atlas ↗</a><a href='http://localhost:8090' target='_blank'>Scenario console ↗</a></div>"
def hero(eyebrow, headline, description):
    return business("", 0, 0, 24, 4, "lab_factory_info", "{{#each data}}<div class='hero'><div><div class='eyebrow'>" + eyebrow + "</div><div class='headline'>" + headline + "</div><div class='subline'>" + description + "</div>" + NAV + "</div><div class='pill'>{{mode}} / {{signal_count}} SIGNALS</div></div>{{/each}}")

DOMAINS_HTML = "{{#each data}}{{#if @first}}<div class='domains'>{{/if}}<div class='domain'><div class='domain-title'>{{title}}</div><div class='status' style='color:{{color}}'>● {{status}}</div><div class='caption'>{{domain}}</div></div>{{#if @last}}</div>{{/if}}{{/each}}"
BRIEF_HTML = "{{#each data}}<div class='brief'><div class='eyebrow'>INCIDENT BRIEF / {{mode}}</div><h3>{{title}}</h3><div class='meta'>{{node}} · {{workload}}</div><p><b>Evidence</b><br>{{evidence}}</p><p><b>Next action</b><br>{{action}}</p><div class='runbook'><a href='http://localhost:8090/runbooks#{{domain}}' target='_blank'>Open {{domain}} runbook ↗</a></div></div>{{/each}}"


def dashboard(uid, title, panels, variables=False):
    for i, p in enumerate(panels, 1):
        p["id"] = i
        expressions = " ".join(t["expr"] for t in p["targets"])
        matched = [s for s in SIGNALS if s["name"] in expressions]
        if matched:
            links = {s["source_url"]: SOURCES[s["source"]][0] for s in matched}
            p["links"] = [{"title": label + " · original docs", "url": url, "targetBlank": True} for url, label in links.items()]
            p["description"] = (p["description"] + "\n" if p["description"] else "") + "\n".join(s["name"] + ": " + s["meaning"] + " Unit: " + s["unit"] + ". " + s["naming"] + "." for s in matched)
    return {"uid": uid, "title": title, "description": "AI Factory Reliability Lab. Default vendor and workload feeds are simulated. Origins remain visible. Source-linked documentation accompanies every signal.", "schemaVersion": 41, "version": 1, "editable": True, "tags": ["ai-factory", "nvidia", "observability-lab"], "timezone": "browser", "refresh": "5s", "time": {"from": "now-30m", "to": "now"}, "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m"]}, "style": "dark", "panels": panels, "annotations": {"list": []}, "templating": {"list": [{"name": "source", "type": "query", "label": "Source", "datasource": DS, "query": "label_values(lab_source_up, source)", "definition": "label_values(lab_source_up, source)", "refresh": 1, "includeAll": True, "allValue": ".*", "multi": True, "current": {"text": "All", "value": "$__all"}}] if variables else []}, "links": [{"title": "NVIDIA framework", "url": "https://developer.nvidia.com/blog/how-to-choose-full-stack-observability-for-nvidia-ai-factories/", "targetBlank": True}, {"title": "Scenario console", "url": "http://localhost:8090", "targetBlank": True}]}


def fixed_color(p, color="#b7f77b"):
    p["fieldConfig"]["defaults"]["color"] = {"mode": "fixed", "fixedColor": color}
    return p


def topology(x, y, w, h):
    p = panel("nodeGraph", "Fabric map · demo inventory", x, y, w, h, targets=[target("lab_topology_node_info", "nodes", True, True), target('lab_topology_edge_info{source=~".+",target=~".+"}', "edges", True, True)], description="A topology inventory with rule-derived node status. Default inventory is synthetic; replace it for native deployments.")
    p["options"] = {"nodes": {"mainStatUnit": "short"}, "edges": {"mainStatUnit": "short"}, "zoomMode": "fit"}
    return p


def overview():
    p = [hero("AI FACTORY / OPERATIONS 01", "A clear view of the whole factory.", "GPU, node, fabric and workload evidence on one timeline. Every demo feed is labeled.")]
    stats = [("Active hypotheses", "lab_incident_count", "short"), ("Feeds available", "100 * sum(lab_source_up) / count(lab_source_up)", "percent"), ("Demo GPU allocation", "lab_allocated_gpus", "short"), ("Training / baseline", "100 * lab:training_throughput_ratio", "percent"), ("Inference TTFT · p95", "lab:inference_ttft_p95_seconds", "s"), ("Lost capacity estimate", "lab_capacity_lost_gpu_hours_total", "suffix:GPU·h")]
    for i, (title, expr, unit) in enumerate(stats):
        p.append(fixed_color(panel("stat", title, i * 4, 4, 4, 4, expr, unit)))
    p += [business("Domain compass", 0, 8, 24, 5, "lab_domain_status", DOMAINS_HTML),
          panel("timeseries", "Useful work · training and inference", 0, 13, 16, 8, targets=[target('rate(lab_training_tokens_total{workload="train-42"}[1m])', "A", legend="Training tokens/s"), target('rate(generation_tokens_total[1m])', "B", legend="Inference tokens/s")], unit="suffix:tokens/s"),
          business("Evidence → action", 16, 13, 8, 8, "lab_incident_info", BRIEF_HTML),
          topology(0, 21, 12, 10),
          panel("bargauge", "Collector heartbeat", 12, 21, 6, 10, "lab_source_up", legend="{{source}}", options={"displayMode": "basic", "text": {"titleSize": 10, "valueSize": 10}}),
          panel("gauge", "GPU thermal envelope", 18, 21, 6, 10, "max(DCGM_FI_DEV_GPU_TEMP)", "celsius"),
          panel("state-timeline", "Domain history · unknown stays visible", 0, 31, 14, 8, "lab_domain_status", legend="{{title}}", options={"showValue": "never", "rowHeight": 0.8, "mergeValues": True, "legend": {"showLegend": False}, "tooltip": {"mode": "single"}}),
          panel("stat", "GPU activity deck", 14, 31, 10, 8, "DCGM_FI_DEV_GPU_UTIL", "percent", "{{node}} / GPU {{gpu}}", options={"textMode": "value_and_name", "orientation": "horizontal", "graphMode": "none"}),
          panel("table", "Routing ledger · firing and pending alerts", 0, 39, 16, 7, targets=[target("ALERTS", table=True, instant=True)], description="Prometheus alerts route to Alertmanager and the local webhook ledger."),
          panel("piechart", "Provenance · source modes", 16, 39, 8, 7, targets=[target("sum by (mode) (lab_source_up)", instant=True, legend="{{mode}}")], options={"pieType": "donut", "displayLabels": ["name", "value"], "legend": {"showLegend": True, "placement": "bottom", "displayMode": "list"}, "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}})]
    p[11]["fieldConfig"]["defaults"].update({"min": 0, "max": 1, "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "#b7f77b", "value": 1}]}})
    p[11]["fieldConfig"]["defaults"]["color"] = {"mode": "thresholds"}
    p[12]["fieldConfig"]["defaults"].update({"min": 0, "max": 100, "color": {"mode": "thresholds"}})
    for item in p:
        if item["type"] == "state-timeline":
            item["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {"0": {"text": "Nominal", "color": "#a8e878"}, "2": {"text": "Investigate", "color": "#ff9770"}, "3": {"text": "Unknown", "color": "#bca8ff"}}}]
    return dashboard("factory-overview", "Factory / Overview", p)


def fabric():
    p = [hero("AI FACTORY / FABRIC 02", "Find the link that holds the job back.", "Compare bit errors, congestion and the slowest collective. Thresholds are lab examples.")]
    p += [business("Fabric status", 0, 4, 16, 5, 'lab_domain_status{domain=~"infiniband|ethernet|nvlink"}', DOMAINS_HTML, CSS.replace("repeat(7,", "repeat(3,")),
          business("Operator brief", 16, 4, 8, 10, 'lab_incident_info', BRIEF_HTML),
          panel("timeseries", "Bit error ratios · post-FEC and pre-FEC", 0, 9, 8, 8, targets=[target('max(lab_ufm_effective_ber_ratio)', "A", legend="Effective BER"), target('max(lab_ufm_raw_ber_ratio)', "B", legend="Raw BER")], unit="sci"),
          panel("bargauge", "Symbol error rate by port", 8, 9, 8, 8, "rate(lab_ufm_symbol_errors_total[1m])", "suffix:errors/s", "port {{port}}"),
          panel("timeseries", "NCCL · the slowest rank matters", 16, 14, 8, 10, 'lab_nccl_collective_seconds{workload="train-42"}', "s", "rank {{rank}} / {{node}}"),
          topology(0, 17, 16, 11),
          panel("timeseries", "InfiniBand traffic", 0, 28, 8, 8, "rate(lab_ufm_port_xmit_bytes_total[1m])", "Bps", "port {{port}}"),
          panel("timeseries", "RoCE · ECN and packet drops", 8, 28, 8, 8, targets=[target("rate(lab_netq_ecn_marked_packets_total[1m])", "A", legend="ECN marked/s"), target("rate(lab_netq_dropped_packets_total[1m])", "B", legend="Dropped/s")], unit="suffix:packets/s"),
          panel("timeseries", "Rack NVLink throughput", 16, 24, 8, 12, "rate(lab_nmx_link_bytes_total[1m])", "Bps", "{{rack}} / {{link}}"),
          panel("gauge", "RoCE buffer pressure", 0, 36, 6, 7, "lab_netq_buffer_usage_ratio", "percentunit"),
          panel("stat", "PFC pause time / second", 6, 36, 6, 7, "rate(lab_netq_pfc_pause_seconds_total[1m])", "s"),
          panel("status-history", "NVLink link health", 12, 36, 12, 7, "lab_nmx_link_healthy", legend="{{rack}} / {{link}}", options={"showValue": "never", "legend": {"showLegend": False}, "rowHeight": 0.7})]
    p[3]["fieldConfig"]["defaults"]["custom"]["scaleDistribution"] = {"type": "log", "log": 10}
    p[-1]["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {"0": {"text": "Unhealthy", "color": "#ff9770"}, "1": {"text": "Healthy", "color": "#a8e878"}}}]
    p[-1]["maxDataPoints"] = 60
    p[-1]["interval"] = "30s"
    for item in p:
        if item["type"] == "gauge":
            item["fieldConfig"]["defaults"].update({"min": 0, "max": 1, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": .8}, {"color": "red", "value": .9}]}})
    return dashboard("factory-fabric", "Factory / Fabric investigations", p)


def workloads():
    p = [hero("AI FACTORY / WORKLOADS 03", "Measure useful work, not just busy GPUs.", "Training progress, scheduling fairness and inference experience, side by side.")]
    p += [panel("timeseries", "Training steps · every rank", 0, 4, 12, 8, 'lab_training_step_seconds{workload="train-42"}', "s", "rank {{rank}}"),
          panel("timeseries", "First token and completion · p95", 12, 4, 12, 8, targets=[target("lab:inference_ttft_p95_seconds", "A", legend="TTFT p95"), target("histogram_quantile(0.95, sum by (le) (rate(e2e_request_latency_seconds_bucket[1m])))", "B", legend="Completion p95")], unit="s"),
          panel("heatmap", "First-token latency · distribution over time", 0, 12, 12, 9, targets=[{**target("sum by (le) (rate(time_to_first_token_seconds_bucket[1m]))", legend="{{le}}"), "format": "heatmap"}], options={"calculate": False, "yAxis": {"unit": "s", "axisPlacement": "left"}, "color": {"mode": "scheme", "scheme": "Spectral", "reverse": True, "steps": 64}, "legend": {"show": True}, "tooltip": {"show": True, "yHistogram": True}}),
          business("Workload incident brief", 12, 12, 12, 9, "lab_incident_info", BRIEF_HTML),
          panel("gauge", "KV-cache occupancy", 0, 21, 6, 7, "gpu_cache_usage_perc", "percentunit"),
          panel("stat", "Generation success", 6, 21, 6, 7, "100 * lab:inference_success_ratio", "percent"),
          panel("timeseries", "Request queue and active work", 12, 21, 12, 7, targets=[target("num_requests_running", "A", legend="Running requests"), target("num_requests_waiting", "B", legend="Waiting requests")]),
          panel("barchart", "Allocation and quota by project", 0, 28, 12, 8, targets=[target("lab_runai_allocated_gpus", "A", True, True), target("lab_runai_quota_gpus", "B", True, True)], options={"orientation": "vertical", "stacking": "none", "showValue": "always", "groupWidth": 0.65, "barWidth": 0.85, "xField": "project", "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"}}),
          panel("timeseries", "Queue waits · scheduler context", 12, 28, 12, 8, targets=[target("max(lab_bcm_queue_wait_seconds)", "A", legend="BCM"), target("max(lab_slurm_queue_wait_seconds)", "B", legend="Slurm"), target("max(lab_runai_queue_wait_seconds)", "C", legend="Run:ai")], unit="s"),
          panel("stat", "Idle allocated GPUs", 0, 36, 6, 7, "lab_bcm_idle_allocated_gpus"),
          panel("table", "NIM Operator resource states", 6, 36, 10, 7, targets=[target('{__name__=~"nimCache_status_total|nimService_status_total|nimPipeline_status_total"}', table=True, instant=True)]),
          panel("timeseries", "Input, compute and platform temperature", 16, 36, 8, 7, "DCGM_FI_DEV_GPU_TEMP", "celsius", "{{node}} / {{gpu}}")]
    p[8]["transformations"] = [{"id": "joinByField", "options": {"byField": "project", "mode": "outerTabular"}}, {"id": "organize", "options": {"excludeByName": {"Time": True, "Time 1": True, "Time 2": True, "cluster 1": True, "cluster 2": True, "origin 1": True, "origin 2": True, "source 1": True, "source 2": True}, "renameByName": {"Value #A": "Allocated", "Value #B": "Quota"}}}]
    p[5]["fieldConfig"]["defaults"].update({"min": 0, "max": 1, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": .8}, {"color": "red", "value": .95}]}})
    return dashboard("factory-workloads", "Factory / Training and inference", p)


def atlas():
    p = [hero("AI FACTORY / SIGNAL ATLAS 04", "Every signal has a source and a purpose.", "Native names, normalized contracts, units and original documentation. Availability is measured.")]
    p += [business("Exporter passports", 0, 4, 24, 12, 'lab_source_up{source=~"$source"}', "{{#each data}}{{#if @first}}<div class='source-grid'>{{/if}}<div class='source'><b>{{source_title}}</b><small>{{domain}} · {{mode}}</small><small>Feed available: {{Value}}</small><a href='{{source_url}}' target='_blank'>Original documentation ↗</a></div>{{#if @last}}</div>{{/if}}{{/each}}"),
          panel("table", "Signal dictionary · original docs are one click away", 0, 16, 24, 19, targets=[target('lab_signal_available{source=~"$source"}', table=True, instant=True)], options={"showHeader": True, "cellHeight": "sm", "sortBy": [{"displayName": "source", "desc": False}]}),
          panel("bargauge", "Expected signal coverage by source", 0, 35, 14, 9, "100 * sum by (source) (lab_signal_available) / count by (source) (lab_signal_available)", "percent", "{{source}}"),
          panel("timeseries", "Age of last successful collection", 14, 35, 10, 9, "time() - lab_source_last_update_unixtime_seconds", "s", "{{source}}")]
    p[2]["transformations"] = [{"id": "organize", "options": {"excludeByName": {"Time": True, "cluster": True, "origin": True, "__name__": True, "instance": True, "job": True}, "indexByName": {"source": 0, "metric": 1, "Value": 2, "mode": 3, "metric_type": 4, "unit": 5, "original_field": 6, "naming": 7, "source_url": 8}, "renameByName": {"Value": "Available", "source_url": "Original docs", "original_field": "Original field", "metric_type": "Type", "metric": "Signal"}}}]
    p[2]["fieldConfig"]["overrides"] = [{"matcher": {"id": "byName", "options": "Original docs"}, "properties": [{"id": "links", "value": [{"title": "Open original documentation", "url": "${__value.raw}", "targetBlank": True}]}, {"id": "custom.width", "value": 160}]}, {"matcher": {"id": "byName", "options": "Available"}, "properties": [{"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "Missing", "color": "#ff9770"}, "1": {"text": "Available", "color": "#a8e878"}}}]}, {"id": "custom.cellOptions", "value": {"type": "color-text"}}]}]
    return dashboard("factory-signals", "Factory / Signal atlas", p, True)


def write_json(path, obj):
    (ROOT / path).write_text(json.dumps(obj, indent=2) + "\n")


def configs():
    scrape = [{"job_name": "lab", "metrics_path": "/metrics/lab", "static_configs": [{"targets": ["lab:8090"]}]}]
    for source in SOURCES:
        scrape.append({"job_name": source, "metrics_path": f"/metrics/{source}", "static_configs": [{"targets": ["lab:8090"]}]})
    write_json("config/prometheus.yml", {"global": {"scrape_interval": "5s", "evaluation_interval": "5s"}, "rule_files": ["/etc/prometheus/rules.yml"], "alerting": {"alertmanagers": [{"static_configs": [{"targets": ["alertmanager:9093"]}]}]}, "scrape_configs": scrape})
    records = [
        {"record": "lab:training_throughput_ratio", "expr": "rate(lab_training_tokens_total[1m]) / on(workload, cluster, origin) lab_training_baseline_tokens_per_second"},
        {"record": "lab:inference_success_ratio", "expr": "rate(request_success_total[1m]) / clamp_min(rate(request_success_total[1m]) + rate(request_failure_total[1m]), 0.000001)"},
        {"record": "lab:inference_ttft_p95_seconds", "expr": "histogram_quantile(0.95, sum by (le, cluster, origin) (rate(time_to_first_token_seconds_bucket[1m])))"},
    ]
    alerts = []
    def alert(name, expr, domain, owner, action, duration="10s"):
        alerts.append({"alert": name, "expr": expr, "for": duration, "labels": {"severity": "warning", "domain": domain, "owner": owner}, "annotations": {"summary": action, "runbook_url": "http://localhost:8090/runbooks#" + domain, "dashboard_url": "http://localhost:3000/d/factory-overview", "scope": "Lab thresholds; validate against real workload baselines before production use."}})
    alert("TelemetrySourceUnavailable", "lab_source_up == 0", "telemetry", "observability", "Restore the unavailable source; domain health is unknown.")
    alert("GpuXidObserved", "DCGM_FI_DEV_XID_ERRORS > 0", "gpu", "gpu-platform", "Classify the observed XID code and inspect the node.")
    alert("PlatformThermalFault", "DCGM_FI_DEV_GPU_TEMP > 85", "platform", "datacenter", "Inspect cooling, power and clock limiting.")
    alert("StorageHealthFault", "lab_nvsm_storage_healthy == 0", "platform", "gpu-platform", "Inspect local storage and input pipeline health.")
    alert("InfiniBandGrayFailure", '(max by (cluster, origin, node, workload) (lab_nccl_collective_seconds{workload="train-42"}) > 0.08) and on (cluster, origin, node) (max by (cluster, origin, node) (lab_ufm_effective_ber_ratio) > 1e-10)', "infiniband", "fabric", "Inspect the affected InfiniBand port and cable.")
    alert("RoceCongestion", "lab_netq_buffer_usage_ratio > 0.85", "ethernet", "fabric", "Inspect RoCE buffers, PFC and ECN.")
    alert("NvlinkDomainDegraded", "lab_nmx_link_healthy == 0", "nvlink", "fabric", "Inspect the NVLink domain and partition.")
    alert("SchedulingStarvation", "(lab_runai_queue_wait_seconds > 120) and on (cluster, origin, project) (lab_runai_idle_allocated_gpus > 0)", "scheduling", "ml-platform", "Review quotas and idle reservations.")
    alert("InferenceCapacityPressure", "gpu_cache_usage_perc > 0.9", "inference", "serving", "Inspect queue depth and concurrency limits.")
    alert("TrainingProgressSlow", "lab:training_throughput_ratio < 0.8", "workload", "training", "Use the triage board to inspect progress and infrastructure.", "20s")
    alert("InferenceLatencySlo", "lab:inference_ttft_p95_seconds > 1.5", "inference", "serving", "Investigate first-token latency with queue and fabric evidence.", "20s")
    alert("InferenceSuccessSlo", "lab:inference_success_ratio < 0.99", "inference", "serving", "Investigate failed model generations.", "20s")
    write_json("config/rules.yml", {"groups": [{"name": "factory-lab", "rules": records + alerts}]})
    write_json("config/alertmanager.yml", {"route": {"receiver": "lab-ledger", "group_by": ["cluster", "origin", "domain", "workload"], "group_wait": "5s", "group_interval": "10s", "repeat_interval": "30m"}, "receivers": [{"name": "lab-ledger", "webhook_configs": [{"url": "http://lab:8090/api/alerts", "send_resolved": True}]}], "inhibit_rules": [{"source_matchers": ['alertname="InfiniBandGrayFailure"'], "target_matchers": ['alertname="TrainingProgressSlow"'], "equal": ["cluster", "origin", "workload"]}]})
    write_json("config/grafana/provisioning/datasources/prometheus.yml", {"apiVersion": 1, "datasources": [{"name": "Factory Prometheus", "uid": "factory-prometheus", "type": "prometheus", "access": "proxy", "url": "http://prometheus:9090", "isDefault": True, "editable": True, "jsonData": {"httpMethod": "POST", "timeInterval": "5s"}}]})
    write_json("config/grafana/provisioning/dashboards/factory.yml", {"apiVersion": 1, "providers": [{"name": "Factory lab", "folder": "AI Factory", "type": "file", "disableDeletion": False, "allowUiUpdates": True, "updateIntervalSeconds": 5, "options": {"path": "/var/lib/grafana/dashboards"}}]})
    write_json("config/sources.example.json", {"dcgm": {"mode": "prometheus", "url": "http://gpu-host:9400/metrics", "labels": {"node": "gpu-host"}, "label_map": {"hostname": "node", "Hostname": "node"}}, "nim": {"mode": "prometheus", "url": "http://gpu-host:8000/v1/metrics", "labels": {"node": "gpu-host"}, "rename": {}, "scale": {}}, "redfish": {"mode": "redfish", "url": "https://bmc.example.invalid", "username_env": "BMC_USERNAME", "password_env": "BMC_PASSWORD", "labels": {"node": "gpu-host"}, "paths": ["/redfish/v1/Chassis/1/Thermal", "/redfish/v1/Chassis/1/Power", "/redfish/v1/Managers/1"]}})
    write_json("config/sources.simulated.json", {k: {"mode": "simulated"} for k in SOURCES})
    lines = ["# Alerts and ownership", "", "Thresholds are deliberately chosen for controlled lab scenarios. They are not NVIDIA production limits. All alerts carry an owner, action, dashboard and runbook URL.", "", "| Alert | Domain | Owner | Hold | Action |", "|---|---|---|---|---|"]
    for a in alerts:
        lines.append(f'| `{a["alert"]}` | {a["labels"]["domain"]} | {a["labels"]["owner"]} | {a["for"]} | {a["annotations"]["summary"]} |')
    lines += ["", "Only the matching training symptom is inhibited by the InfiniBand cause alert, using cluster, origin and workload equality. Unrelated workloads retain their notifications.", "", "```mermaid", "flowchart LR", "  P[Prometheus rules] --> A[Alertmanager grouping and inhibition]", "  A --> W[Local webhook ledger]", "  W --> C[Scenario console]", "```", ""]
    (ROOT / "docs/alerts.md").write_text("\n".join(lines))


def main():
    export_catalog(ROOT)
    boards = [overview(), fabric(), workloads(), atlas()]
    for board in boards:
        write_json("dashboards/" + board["uid"] + ".json", board)
    configs()
    kinds = sorted({p["type"] for d in boards for p in d["panels"]})
    print(f"Built {len(boards)} dashboards, {sum(len(d['panels']) for d in boards)} panels, {len(kinds)} panel types; {len(SIGNALS)} signals.")


if __name__ == "__main__":
    main()
