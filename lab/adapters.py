"""Live Prometheus, JSON mapping and Redfish adapters. No silent simulation fallback."""
import base64
import json
import math
import os
import ssl
import time
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from .metrics import Sample, parse


def get(url, config):
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("Only HTTP(S) telemetry endpoints are accepted")
    headers = {"Accept": "application/json, text/plain", "User-Agent": "ai-factory-observability-lab/1.0"}
    if config.get("token_env"):
        token = os.environ[config["token_env"]]
        headers["Authorization"] = "Bearer " + token
    if config.get("username_env"):
        username = os.environ[config["username_env"]]
        password = os.environ[config["password_env"]]
        credentials = base64.b64encode((username + ":" + password).encode()).decode()
        headers["Authorization"] = "Basic " + credentials
    context = ssl.create_default_context(cafile=config.get("ca_file"))
    with urlopen(Request(url, headers=headers), timeout=float(config.get("timeout_seconds", 3)), context=context) as response:
        body = response.read(4 * 1024 * 1024 + 1)
        if len(body) > 4 * 1024 * 1024:
            raise ValueError("Telemetry response exceeds 4 MiB")
        return body.decode("utf-8")


def pointer(document, path):
    if path in ("", "/"):
        return document
    current = document
    for token in path.strip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def collect(source, config, state=None):
    mode = config.get("mode", "simulated")
    labels = {"cluster": "factory-lab", **config.get("labels", {}), "source": source, "origin": "live"}
    if mode == "prometheus":
        samples = parse(get(config["url"], config), labels, config.get("rename", {}))
        if source == "dcgm":
            samples = [s for s in samples if abs(s.value) < 9e18]
        for s in samples:
            for key, value in config.get("label_map", {}).items():
                if key in s.labels:
                    s.labels[value] = s.labels[key]
            factor = config.get("scale", {}).get(s.name, 1)
            s.value *= float(factor)
        return accumulate_rates(samples, config.get("counter_from_rate", []), state)
    if mode == "json":
        data = json.loads(get(config["url"], config))
        samples = []
        for mapping in config["mappings"]:
            records = pointer(data, mapping.get("records_pointer", ""))
            if not isinstance(records, list):
                records = [records]
            for record in records:
                try:
                    value = pointer(record, mapping["value_pointer"])
                    if mapping.get("value_map"):
                        value = mapping["value_map"][str(value)]
                    value = float(value) * float(mapping.get("scale", 1))
                    if not math.isfinite(value):
                        continue
                    extra = {key: str(pointer(record, path)) for key, path in mapping.get("label_pointers", {}).items()}
                    samples.append(Sample(mapping["metric"], value, {**labels, **extra}))
                except (KeyError, IndexError, TypeError, ValueError):
                    continue
        names = [m["metric"] for m in config["mappings"] if m.get("counter_from_rate")]
        return accumulate_rates(samples, names, state)
    if mode == "redfish":
        samples = []
        base = config["url"].rstrip("/")
        for path in config["paths"]:
            data = json.loads(get(base + "/" + path.lstrip("/"), config))
            samples.extend(redfish_samples(data, labels))
        return samples
    raise ValueError("Unknown live adapter mode")


def accumulate_rates(samples, names, state=None, now=None):
    """Integrate explicitly declared base-unit rates using held-sample elapsed time."""
    if not names:
        return samples
    if state is None:
        raise ValueError("Rate integration requires persistent adapter state")
    now = time.time() if now is None else now
    for sample in samples:
        if sample.name not in names:
            continue
        key = (sample.name, tuple(sorted(sample.labels.items())))
        previous_time, total = state.get(key, (now, 0))
        total += max(0, sample.value) * max(0, now - previous_time)
        state[key] = (now, total)
        sample.value = total
    return samples


def redfish_samples(data, labels):
    """Thermal/Power schemas and modern Sensor/PowerSupply resource instances."""
    samples = []
    def add(metric, value, sensor):
        if value is not None:
            samples.append(Sample(metric, float(value), {**labels, "sensor": str(sensor)}))
    def health(obj):
        value = obj.get("Status", {}).get("Health")
        return None if value is None else int(value == "OK")
    for sensor in data.get("Fans", []):
        add("lab_redfish_fan_rpm", sensor.get("Reading") if sensor.get("ReadingUnits", "RPM") == "RPM" else None, sensor.get("Name", sensor.get("MemberId", "fan")))
    for sensor in data.get("Temperatures", []):
        add("lab_redfish_temperature_celsius", sensor.get("ReadingCelsius"), sensor.get("Name", "temperature"))
    for psu in data.get("PowerSupplies", []):
        add("lab_redfish_psu_healthy", health(psu), psu.get("Name", "PSU"))
    kind = data.get("@odata.type", "")
    if "PowerSupply." in kind:
        add("lab_redfish_psu_healthy", health(data), data.get("Name", "PSU"))
    if "Manager." in kind:
        add("lab_redfish_bmc_healthy", health(data), data.get("Name", "BMC"))
    if "Sensor." in kind:
        unit = data.get("ReadingUnits")
        if unit in ("Cel", "Celsius"):
            add("lab_redfish_temperature_celsius", data.get("Reading"), data.get("Name", "temperature"))
        elif unit == "RPM":
            add("lab_redfish_fan_rpm", data.get("Reading"), data.get("Name", "fan"))
    return samples
