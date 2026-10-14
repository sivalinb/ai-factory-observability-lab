#!/usr/bin/env python3
"""Run real Grafana/Prometheus/Alertmanager without Docker, using workspace runtimes."""
import argparse
import hashlib
import json
import os
import platform
import secrets
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {"grafana": "12.3.0", "prometheus": "3.5.0", "alertmanager": "0.28.1", "business_text": "6.3.0"}


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temp = path.with_suffix(path.suffix + ".part")
        print("Downloading", url, flush=True)
        with urlopen(url, timeout=30) as response, temp.open("wb") as output:
            shutil.copyfileobj(response, output)
        temp.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(runtime):
    system = platform.system().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine())
    if system not in ("darwin", "linux") or arch is None:
        raise SystemExit("Native mode supports macOS/Linux arm64/amd64; use Docker Compose on other systems.")
    paths, receipts = {}, {}
    for name in ("grafana", "prometheus", "alertmanager"):
        version = VERSIONS[name]
        url = (f"https://dl.grafana.com/oss/release/grafana-{version}.{system}-{arch}.tar.gz" if name == "grafana" else f"https://github.com/prometheus/{name}/releases/download/v{version}/{name}-{version}.{system}-{arch}.tar.gz")
        archive = runtime / "downloads" / (name + ".tar.gz")
        directory = runtime / (f"grafana-{version}" if name == "grafana" else f"{name}-{version}.{system}-{arch}")
        if not directory.exists():
            receipts[name] = {"url": url, "sha256": download(url, archive)}
            with tarfile.open(archive) as tar:
                for item in tar.getmembers():
                    if not (runtime / item.name).resolve().is_relative_to(runtime):
                        raise ValueError("Archive path escapes runtime directory")
                tar.extractall(runtime)
        if not directory.exists():
            candidates = [p for p in runtime.glob(name + "*" + version + "*") if (p / ("bin/grafana" if name == "grafana" else name)).is_file()]
            if len(candidates) != 1:
                raise RuntimeError("Cannot identify the extracted runtime for " + name)
            directory = candidates[0]
        paths[name] = directory
    plugins = runtime / "plugins"
    plugins.mkdir(exist_ok=True)
    if not (plugins / "marcusolsson-dynamictext-panel" / "plugin.json").exists():
        url = f"https://grafana.com/api/plugins/marcusolsson-dynamictext-panel/versions/{VERSIONS['business_text']}/download"
        archive = runtime / "downloads/business-text.zip"
        receipts["business_text"] = {"url": url, "sha256": download(url, archive)}
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                if not (plugins / name).resolve().is_relative_to(plugins):
                    raise ValueError("Plugin path escapes directory")
            zipped.extractall(plugins)
    if receipts:
        (runtime / "download-receipts.json").write_text(json.dumps(receipts, indent=2))
    return paths


def prepare(runtime):
    subprocess.run([sys.executable, str(ROOT / "scripts/build.py")], check=True, cwd=ROOT)
    config = runtime / "config"
    config.mkdir(exist_ok=True)
    prometheus = json.loads((ROOT / "config/prometheus.yml").read_text())
    for job in prometheus["scrape_configs"]:
        job["static_configs"][0]["targets"] = ["127.0.0.1:8090"]
    prometheus["rule_files"] = [str(ROOT / "config/rules.yml")]
    prometheus["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"] = ["127.0.0.1:9093"]
    (config / "prometheus.yml").write_text(json.dumps(prometheus, indent=2))
    alerts = json.loads((ROOT / "config/alertmanager.yml").read_text())
    alerts["receivers"][0]["webhook_configs"][0]["url"] = "http://127.0.0.1:8090/api/alerts"
    (config / "alertmanager.yml").write_text(json.dumps(alerts, indent=2))
    provision = config / "provisioning"
    (provision / "datasources").mkdir(parents=True, exist_ok=True)
    (provision / "dashboards").mkdir(exist_ok=True)
    ds = json.loads((ROOT / "config/grafana/provisioning/datasources/prometheus.yml").read_text())
    ds["datasources"][0]["url"] = "http://127.0.0.1:9090"
    (provision / "datasources/prometheus.yml").write_text(json.dumps(ds, indent=2))
    boards = json.loads((ROOT / "config/grafana/provisioning/dashboards/factory.yml").read_text())
    boards["providers"][0]["options"]["path"] = str(ROOT / "dashboards")
    (provision / "dashboards/factory.yml").write_text(json.dumps(boards, indent=2))
    return config


def wait_ready(url, seconds=25):
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.5)
    raise RuntimeError("Service did not become ready: " + url)


def stop(runtime):
    pid_file = runtime / "pids.json"
    if not pid_file.exists():
        return
    for service, pid in json.loads(pid_file.read_text()).items():
        try:
            os.kill(pid, signal.SIGTERM)
            print("Stopped", service)
        except ProcessLookupError:
            pass
    pid_file.unlink()


def up(runtime, sources, seed):
    if (runtime / "pids.json").exists():
        raise SystemExit("This runtime already has a PID ledger; run status or down first.")
    for port in (3000, 8090, 9090, 9093):
        import socket
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(f"Port {port} is occupied; no existing service was changed.")
    paths = install(runtime)
    config = prepare(runtime)
    logs = runtime / "logs"
    logs.mkdir(exist_ok=True)
    if seed:
        subprocess.run([sys.executable, str(ROOT / "scripts/seed.py"), "--promtool", str(paths["prometheus"] / "promtool"), "--data-dir", str(runtime / "prometheus-data"), "--work-dir", str(runtime / "seed")], check=True, cwd=ROOT)
    commands = {
        "lab": [sys.executable, "-m", "lab.server"] + (["--sources", str(Path(sources).resolve())] if sources else []),
        "alertmanager": [str(paths["alertmanager"] / "alertmanager"), "--config.file=" + str(config / "alertmanager.yml"), "--storage.path=" + str(runtime / "alertmanager-data"), "--web.listen-address=127.0.0.1:9093", "--cluster.listen-address="],
        "prometheus": [str(paths["prometheus"] / "prometheus"), "--config.file=" + str(config / "prometheus.yml"), "--storage.tsdb.path=" + str(runtime / "prometheus-data"), "--storage.tsdb.retention.time=3d", "--web.listen-address=127.0.0.1:9090"],
        "grafana": [str(paths["grafana"] / "bin/grafana"), "server", "--homepath=" + str(paths["grafana"])],
    }
    password_file = runtime / "grafana-admin-password.txt"
    if not password_file.exists():
        password_file.write_text(secrets.token_urlsafe(24))
    password_file.chmod(0o600)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GF_SERVER_HTTP_ADDR="127.0.0.1", GF_SERVER_HTTP_PORT="3000", GF_PATHS_DATA=str(runtime / "grafana-data"), GF_PATHS_LOGS=str(logs), GF_PATHS_PLUGINS=str(runtime / "plugins"), GF_PATHS_PROVISIONING=str(config / "provisioning"), GF_AUTH_ANONYMOUS_ENABLED="true", GF_AUTH_ANONYMOUS_ORG_ROLE="Viewer", GF_USERS_DEFAULT_THEME="dark", GF_SECURITY_ADMIN_PASSWORD=password_file.read_text(), GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=str(ROOT / "dashboards/factory-overview.json"), GF_ANALYTICS_REPORTING_ENABLED="false", GF_ANALYTICS_CHECK_FOR_UPDATES="false", GF_PLUGINS_PREINSTALL_DISABLED="true")
    pids = {}
    try:
        for name, command in commands.items():
            with (logs / (name + ".log")).open("ab") as output:
                proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            pids[name] = proc.pid
        (runtime / "pids.json").write_text(json.dumps(pids, indent=2))
        for url in ("http://127.0.0.1:8090/health", "http://127.0.0.1:9090/-/ready", "http://127.0.0.1:9093/-/ready", "http://127.0.0.1:3000/api/health"):
            wait_ready(url)
    except Exception:
        stop(runtime)
        raise
    print("Grafana http://localhost:3000/d/factory-overview\nScenario console http://localhost:8090\nPrometheus http://localhost:9090\nAlertmanager http://localhost:9093")
    print("Default vendor telemetry: simulated. Admin credentials are generated locally; anonymous access is localhost-only Viewer.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "down", "status"))
    parser.add_argument("--runtime-dir", default=str(ROOT / ".runtime"))
    parser.add_argument("--sources")
    parser.add_argument("--seed", action="store_true", help="Load 45 minutes of labeled synthetic history before starting")
    args = parser.parse_args()
    runtime = Path(args.runtime_dir).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    if args.action == "up":
        up(runtime, args.sources, args.seed)
    elif args.action == "down":
        stop(runtime)
    else:
        for name, port in [("lab", 8090), ("grafana", 3000), ("prometheus", 9090), ("alertmanager", 9093)]:
            try:
                with urlopen(f"http://127.0.0.1:{port}/" + ("health" if name == "lab" else "api/health" if name == "grafana" else "-/ready"), timeout=1) as r:
                    print(name, "ready" if r.status == 200 else r.status)
            except Exception:
                print(name, "not ready")


if __name__ == "__main__":
    main()
