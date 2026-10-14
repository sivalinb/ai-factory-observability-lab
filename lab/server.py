"""Local control plane, source endpoints, provenance and Alertmanager webhook sink."""
import argparse
import json
import mimetypes
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from . import adapters
from .catalog import SIGNALS, SOURCES
from .engine import DOMAINS, NODES, SCENARIOS, Simulator, diagnose
from .metrics import Sample, render

ROOT = Path(__file__).resolve().parents[1]


class Runtime:
    def __init__(self, config=None):
        self.lock = threading.RLock()
        self.config = config or {}
        unknown = set(self.config) - set(SOURCES)
        if unknown:
            raise ValueError("Unknown sources: " + ", ".join(sorted(unknown)))
        self.simulator = Simulator()
        self.samples = {}
        self.up = {}
        self.updated = {}
        self.failures = {}
        self.adapter_state = {key: {} for key in SOURCES}
        self.notifications = []
        self.events = []
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=6)
        self.refresh()

    def refresh(self):
        now = time.time()
        with self.lock:
            synthetic = self.simulator.update(now)
        futures = {}
        for source in SOURCES:
            config = self.config.get(source, {})
            if config.get("mode", "simulated") == "simulated":
                with self.lock:
                    self.samples[source] = synthetic[source]
                    self.up[source] = bool(synthetic[source])
                    self.updated[source] = now if self.up[source] else self.updated.get(source, now - 30)
            else:
                futures[source] = self.executor.submit(adapters.collect, source, config, self.adapter_state[source])
        for source, future in futures.items():
            try:
                collected = future.result(timeout=5)
                if not collected:
                    raise ValueError("No usable telemetry was returned")
                with self.lock:
                    self.samples[source] = collected
                    self.up[source] = True
                    self.updated[source] = now
                    self.failures.pop(source, None)
            except Exception:
                # Suppress stale samples and never replace a failed live source with demo data.
                with self.lock:
                    self.samples[source] = []
                    self.up[source] = False
                    self.failures[source] = "Collection failed; check endpoint, credentials and mappings."

    def loop(self):
        while self.running:
            time.sleep(1)
            self.refresh()

    def set_scenario(self, name):
        with self.lock:
            self.simulator.set_scenario(name)
            self.events.append({"scenario": name, "time": time.time()})
            self.events = self.events[-30:]
        self.refresh()

    def state(self):
        with self.lock:
            incidents, domains = diagnose(self.samples, self.up)
            critical = {"dcgm": {"DCGM_FI_DEV_XID_ERRORS", "DCGM_FI_DEV_GPU_TEMP"}, "ufm": {"lab_ufm_effective_ber_ratio", "lab_ufm_symbol_errors_total"}, "nim": {"request_success_total", "request_failure_total", "time_to_first_token_seconds_bucket"}}
            for source, required in critical.items():
                if self.config.get(source, {}).get("mode", "simulated") == "simulated" or not self.up.get(source):
                    continue
                missing = required - {s.name for s in self.samples.get(source, [])}
                if missing:
                    domain = SOURCES[source][1]
                    if domains.get(domain) == 0:
                        domains[domain] = 3
                    incidents.append({"domain": "telemetry", "title": "Critical signal coverage gap", "evidence": source + ": missing " + ", ".join(sorted(missing)), "action": "Inspect installed-release aliases and availability in the signal atlas.", "node": "collector", "workload": "coverage", "runbook": "/runbooks#telemetry", "confidence": "observed schema gap", "evidence_origin": "live"})
            mode = "simulated" if not any(c.get("mode", "simulated") != "simulated" for c in self.config.values()) else "mixed"
            return {"scenario": self.simulator.scenario, "scenario_title": SCENARIOS[self.simulator.scenario][0],
                    "origin": mode, "sources": [{"id": key, "title": val[0], "domain": val[1],
                    "mode": "simulated" if self.config.get(key, {}).get("mode", "simulated") == "simulated" else "live",
                    "up": self.up.get(key, False), "last_update": self.updated.get(key),
                    "documentation_url": val[2]} for key, val in SOURCES.items()],
                    "incidents": incidents, "domains": domains, "notifications": self.notifications[-10:],
                    "events": self.events[-10:], "signal_count": len(SIGNALS)}

    def meta(self):
        state = self.state()
        common = {"cluster": "factory-lab", "origin": state["origin"]}
        samples = []
        def add(metric_name, value, **labels):
            samples.append(Sample(metric_name, float(value), {**common, **labels}))
        add("lab_factory_info", 1, scenario=state["scenario_title"], mode=state["origin"], source_count=str(len(SOURCES)), signal_count=str(len(SIGNALS)))
        add("lab_incident_count", len(state["incidents"]))
        add("lab_allocated_gpus", 8, scope="demo inventory")
        add("lab_notifications_total", len(self.notifications))
        for s in state["sources"]:
            add("lab_source_up", int(s["up"]), source=s["id"], source_title=s["title"], mode=s["mode"], domain=s["domain"], source_url=s["documentation_url"])
            add("lab_source_last_update_unixtime_seconds", s["last_update"] or 0, source=s["id"], mode=s["mode"])
        available = {s.name for group in self.samples.values() for s in group}
        for s in SIGNALS:
            exists = s["name"] in available or s["name"] + "_bucket" in available
            mode = "simulated" if self.config.get(s["source"], {}).get("mode", "simulated") == "simulated" else "live"
            add("lab_signal_available", int(exists), source=s["source"], metric=s["name"], unit=s["unit"], metric_type=s["type"], naming=s["naming"], original_field=s["original_field"], source_url=s["source_url"], mode=mode)
        for domain, title in DOMAINS.items():
            value = state["domains"][domain]
            status, color = {0: ("NOMINAL", "#a8e878"), 2: ("INVESTIGATE", "#ff9770"), 3: ("UNKNOWN", "#bca8ff")}[value]
            add("lab_domain_status", value, domain=domain, title=title, status=status, color=color)
        if not state["incidents"]:
            add("lab_incident_info", 0, title="Healthy baseline", domain="none", evidence="No configured rule found an incident in the available signals.", action="Explore a controlled scenario using the lab console.", node="factory", workload="all demo workloads", runbook="http://localhost:8090/runbooks", mode=state["origin"])
        else:
            for incident in state["incidents"]:
                add("lab_incident_info", 1, **{key: val for key, val in incident.items() if key != "confidence"}, mode=state["origin"])
        node_titles = {"dgx-01": "DGX 01", "dgx-02": "DGX 02", "eth-01": "Inference", "nvl-01": "NVLink rack", "ib-leaf-01": "IB leaf", "spectrum-01": "Spectrum", "nv-switch-01": "NVSwitch"}
        impaired = {i["node"] for i in state["incidents"]}
        if state["domains"]["infiniband"] == 2:
            impaired.add("ib-leaf-01")
        if state["domains"]["ethernet"] == 2:
            impaired.add("spectrum-01")
        if state["domains"]["nvlink"] == 2:
            impaired.add("nv-switch-01")
        for node, title in node_titles.items():
            add("lab_topology_node_info", 1, id=node, title=title, subTitle="demo inventory", mainStat="2 GPUs" if node in NODES else "fabric", color="#ff9770" if node in impaired else "#a8e878")
        for i, (src, target, fabric) in enumerate([("ib-leaf-01", "dgx-01", "InfiniBand"), ("ib-leaf-01", "dgx-02", "InfiniBand"), ("spectrum-01", "eth-01", "RoCE"), ("nv-switch-01", "nvl-01", "NVLink")]):
            add("lab_topology_edge_info", 1, id=f"edge-{i}", source=src, target=target, mainStat=fabric)
        return samples


class Handler(BaseHTTPRequestHandler):
    runtime = None
    def log_message(self, fmt, *args):
        if not self.path.startswith("/metrics"):
            super().log_message(fmt, *args)
    def send(self, body, code=200, content_type="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send({"status": "ok"})
        if path == "/api/state":
            return self.send(self.runtime.state())
        if path == "/api/catalog":
            return self.send({"sources": SOURCES, "signals": SIGNALS})
        if path == "/api/scenarios":
            return self.send({k: {"title": v[0], "description": v[1]} for k, v in SCENARIOS.items()})
        if path == "/metrics/lab":
            return self.send(render(self.runtime.meta()), content_type="text/plain; version=0.0.4")
        if path.startswith("/metrics/"):
            source = path.split("/")[-1]
            if source in SOURCES:
                with self.runtime.lock:
                    return self.send(render(self.runtime.samples.get(source, [])), content_type="text/plain; version=0.0.4")
        if path == "/runbooks":
            return self.send((ROOT / "lab/runbooks.html").read_bytes(), content_type="text/html; charset=utf-8")
        if path == "/":
            return self.send((ROOT / "lab/console.html").read_bytes(), content_type="text/html; charset=utf-8")
        if path.startswith("/docs/"):
            file = (ROOT / path.lstrip("/")).resolve()
            if file.is_relative_to(ROOT / "docs") and file.is_file():
                return self.send(file.read_bytes(), content_type="text/plain; charset=utf-8")
        self.send({"error": "Not found"}, 404)
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 65536:
            return self.send({"error": "Request too large"}, 413)
        try:
            data = json.loads(self.rfile.read(length))
            if self.path == "/api/scenario":
                self.runtime.set_scenario(data["scenario"])
                return self.send(self.runtime.state())
            if self.path == "/api/alerts":
                with self.runtime.lock:
                    self.runtime.notifications.append({"received_at": time.time(), "status": data.get("status"), "group_labels": data.get("groupLabels", {}), "alerts": [{"status": a.get("status"), "labels": a.get("labels"), "annotations": a.get("annotations")} for a in data.get("alerts", [])]})
                    self.runtime.notifications = self.runtime.notifications[-100:]
                return self.send({"received": True})
        except (ValueError, KeyError, TypeError):
            return self.send({"error": "Invalid scenario or request"}, 400)
        self.send({"error": "Not found"}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--sources", default=os.environ.get("LAB_SOURCES_CONFIG"))
    args = parser.parse_args()
    config = json.loads(Path(args.sources).read_text()) if args.sources else {}
    runtime = Runtime(config)
    Handler.runtime = runtime
    threading.Thread(target=runtime.loop, daemon=True).start()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Lab console http://{args.host}:{args.port}; default hardware telemetry is simulated", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.running = False
        runtime.executor.shutdown(wait=False)
        httpd.server_close()


if __name__ == "__main__":
    main()
