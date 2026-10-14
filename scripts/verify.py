#!/usr/bin/env python3
"""Check running services and optionally verify fault → scrape → alert → webhook."""
import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.catalog import SOURCES, SIGNALS


def request(url, body=None):
    req = Request(url, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=5) as response:
        return json.loads(response.read())


def query(expr):
    return request("http://localhost:9090/api/v1/query?" + urlencode({"query": expr}))["data"]["result"]


def wait_until(check, timeout=50):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = check()
        if result:
            return result
        time.sleep(1)
    raise AssertionError("Timed out waiting for the expected telemetry transition")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--faults", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = {"services": {}, "dashboards": [], "query_errors": [], "fault_checks": []}
    report["services"]["lab"] = request("http://localhost:8090/health")["status"]
    report["services"]["grafana"] = request("http://localhost:3000/api/health")["database"]
    targets = request("http://localhost:9090/api/v1/targets")["data"]["activeTargets"]
    assert len(targets) == len(SOURCES) + 1
    assert all(t["health"] == "up" for t in targets), [(t["labels"]["job"], t["lastError"]) for t in targets if t["health"] != "up"]
    report["scrape_targets"] = {t["labels"]["job"]: t["health"] for t in targets}
    assert len(query("lab_signal_available")) == len(SIGNALS)
    for file in (ROOT / "dashboards").glob("*.json"):
        board = json.loads(file.read_text())
        actual = request("http://localhost:3000/api/dashboards/uid/" + board["uid"])
        assert actual["dashboard"]["uid"] == board["uid"]
        report["dashboards"].append({"uid": board["uid"], "panels": len(board["panels"])})
        for panel in board["panels"]:
            for target in panel["targets"]:
                expr = target["expr"].replace("$source", ".*")
                try:
                    query(expr)
                except Exception:
                    report["query_errors"].append({"panel": panel["title"], "query": expr})
    assert not report["query_errors"], report["query_errors"]
    if args.faults:
        try:
            for scenario, domain in [("gpu_xid", "gpu"), ("thermal", "platform"), ("roce_congestion", "ethernet"), ("nvlink_degradation", "nvlink"), ("scheduler_starvation", "scheduling"), ("inference_overload", "inference"), ("storage_stall", "platform")]:
                state = request("http://localhost:8090/api/scenario", {"scenario": scenario})
                assert domain in {i["domain"] for i in state["incidents"]}
                report["fault_checks"].append({"scenario": scenario, "domain": domain, "analyzer": "passed"})
            baseline_notifications = len(request("http://localhost:8090/api/state")["notifications"])
            start = time.monotonic()
            request("http://localhost:8090/api/scenario", {"scenario": "ib_gray_failure"})
            wait_until(lambda: query('ALERTS{alertname="InfiniBandGrayFailure",alertstate="firing"}'))
            wait_until(lambda: any(any(a["labels"].get("alertname") == "InfiniBandGrayFailure" and a["status"] == "firing" for a in n["alerts"]) for n in request("http://localhost:8090/api/state")["notifications"]))
            report["fault_checks"].append({"scenario": "ib_gray_failure", "prometheus_alert": "firing", "alertmanager_webhook": "received", "seconds_to_webhook": round(time.monotonic() - start, 2)})
            request("http://localhost:8090/api/scenario", {"scenario": "telemetry_gap"})
            wait_until(lambda: query('lab_source_up{source="ufm"} == 0'))
            assert request("http://localhost:8090/api/state")["domains"]["infiniband"] == 3
            report["fault_checks"].append({"scenario": "telemetry_gap", "domain": "unknown", "prometheus_source_up": 0})
        finally:
            request("http://localhost:8090/api/scenario", {"scenario": "normal"})
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
