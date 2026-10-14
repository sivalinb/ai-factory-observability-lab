import json
import math
import unittest
from pathlib import Path
from unittest.mock import patch
from lab.adapters import collect, redfish_samples, accumulate_rates
from lab.catalog import SIGNALS, SOURCES
from lab.engine import Simulator, diagnose, SCENARIOS
from lab.metrics import Sample, parse, render
from lab.server import Runtime


class SimulationTests(unittest.TestCase):
    def test_every_catalog_signal_is_emitted(self):
        sim = Simulator(1000)
        names = {s.name for group in sim.samples.values() for s in group}
        for spec in SIGNALS:
            expected = spec["name"] + "_bucket" if spec["type"] == "histogram" else spec["name"]
            self.assertIn(expected, names, spec["source"])

    def test_scenarios_resolve_to_the_expected_domain(self):
        expected = {"normal": None, "ib_gray_failure": "infiniband", "gpu_xid": "gpu", "thermal": "platform", "roce_congestion": "ethernet", "nvlink_degradation": "nvlink", "scheduler_starvation": "scheduling", "inference_overload": "inference", "storage_stall": "platform", "telemetry_gap": "telemetry"}
        sim = Simulator(1000)
        for i, scenario in enumerate(SCENARIOS):
            sim.set_scenario(scenario)
            data = sim.update(1001 + i)
            incidents, status = diagnose(data, {k: bool(v) for k, v in data.items()})
            domains = {x["domain"] for x in incidents}
            self.assertEqual(domains, {expected[scenario]} if expected[scenario] else set(), scenario)
            if scenario == "telemetry_gap":
                self.assertEqual(status["infiniband"], 3)

    def test_counters_never_decrease_when_scenario_changes(self):
        counters = {s["name"] for s in SIGNALS if s["type"] == "counter"}
        sim = Simulator(1000)
        previous = {}
        for i, scenario in enumerate(SCENARIOS):
            sim.set_scenario(scenario)
            for group in sim.update(1001 + i).values():
                for sample in group:
                    if sample.name not in counters and not sample.name.endswith(("_bucket", "_count", "_sum")):
                        continue
                    key = (sample.name, tuple(sorted(sample.labels.items())))
                    self.assertGreaterEqual(sample.value, previous.get(key, 0))
                    previous[key] = sample.value

    def test_histogram_buckets_are_cumulative_and_infinity_matches_count(self):
        sim = Simulator(1000)
        for scenario in SCENARIOS:
            sim.set_scenario(scenario)
            data = sim.update(sim.last_tick + 5)["nim"]
            for family in ("time_to_first_token_seconds", "time_per_output_token_seconds", "e2e_request_latency_seconds"):
                buckets = sorted((float(s.labels["le"]), s.value) for s in data if s.name == family + "_bucket")
                self.assertEqual([v for _, v in buckets], sorted(v for _, v in buckets))
                count = next(s.value for s in data if s.name == family + "_count")
                self.assertAlmostEqual(buckets[-1][1], count)

    def test_analyzer_does_not_read_the_scenario_name(self):
        sim = Simulator(1000)
        sim.set_scenario("ib_gray_failure")
        data = sim.update(1001)
        sim.set_scenario("normal")
        incidents, _ = diagnose(data, {k: True for k in data})
        self.assertIn("infiniband", {i["domain"] for i in incidents})

    def test_unrelated_nodes_and_origins_do_not_form_a_fabric_hypothesis(self):
        cause = Sample("lab_ufm_effective_ber_ratio", 1e-8, {"node": "node-a", "origin": "live"})
        for labels in ({"node": "node-b", "origin": "live"}, {"node": "node-a", "origin": "simulated"}):
            data = {"ufm": [cause], "workload": [Sample("lab_nccl_collective_seconds", .2, labels)]}
            incidents, _ = diagnose(data, {"ufm": True, "workload": True})
            self.assertEqual(incidents, [])

    def test_metadata_is_valid_and_exposes_original_links(self):
        runtime = Runtime()
        try:
            meta = runtime.meta()
            roundtrip = parse(render(meta))
            self.assertEqual(len(meta), len(roundtrip))
            dictionary = [s for s in meta if s.name == "lab_signal_available"]
            self.assertEqual(len(dictionary), len(SIGNALS))
            self.assertTrue(all(s.value == 1 for s in dictionary))
            self.assertTrue(all(s.labels["source_url"].startswith("https://") for s in dictionary))
        finally:
            runtime.executor.shutdown()


class AdapterTests(unittest.TestCase):
    def test_unsupported_dcgm_sentinel_is_missing_not_a_hot_gpu(self):
        body = "DCGM_FI_DEV_GPU_UTIL 70\nDCGM_FI_DEV_GPU_TEMP 9223372036854775794\n"
        with patch("lab.adapters.get", return_value=body):
            values = collect("dcgm", {"mode": "prometheus", "url": "http://example.invalid"})
        self.assertEqual([s.name for s in values], ["DCGM_FI_DEV_GPU_UTIL"])

    def test_live_endpoint_with_missing_critical_fields_is_unknown(self):
        with patch("lab.adapters.collect", return_value=[Sample("DCGM_FI_DEV_GPU_UTIL", 70, {"origin": "live"})]):
            runtime = Runtime({"dcgm": {"mode": "prometheus", "url": "http://example.invalid"}})
        try:
            self.assertTrue(runtime.up["dcgm"])
            state = runtime.state()
            self.assertEqual(state["domains"]["gpu"], 3)
            self.assertIn("Critical signal coverage gap", {i["title"] for i in state["incidents"]})
        finally:
            runtime.executor.shutdown()

    def test_prometheus_labels_escaping_and_provenance(self):
        sample = Sample("metric", 4, {"description": 'a "quote" and \\slash\nline', "origin": "simulated"})
        parsed = parse(render([sample]), {"origin": "live"})[0]
        self.assertEqual(parsed.labels["description"], sample.labels["description"])
        self.assertEqual(parsed.labels["origin"], "live")

    def test_histogram_rename_preserves_bucket_suffix(self):
        with patch("lab.adapters.get", return_value='vendor_latency_bucket{le="1"} 2\nvendor_latency_count 3\n'):
            data = collect("nim", {"mode": "prometheus", "url": "http://example.invalid", "rename": {"vendor_latency": "time_to_first_token_seconds"}})
        self.assertEqual(data[0].name, "time_to_first_token_seconds_bucket")
        self.assertEqual(data[0].labels["le"], "1")

    def test_json_mapping_handles_records_scale_and_health_enums(self):
        body = {"ports": [{"id": "17", "bits": 80, "health": "OK"}]}
        config = {"mode": "json", "url": "http://example.invalid", "mappings": [{"records_pointer": "/ports", "value_pointer": "/bits", "metric": "lab_bytes", "scale": .125, "label_pointers": {"port": "/id"}}, {"records_pointer": "/ports", "value_pointer": "/health", "metric": "lab_health", "value_map": {"OK": 1, "Critical": 0}}]}
        with patch("lab.adapters.get", return_value=json.dumps(body)):
            data = collect("netq", config)
        self.assertEqual(data[0].value, 10)
        self.assertEqual(data[0].labels["port"], "17")
        self.assertEqual(data[1].value, 1)

    def test_redfish_does_not_invent_health_for_missing_status(self):
        data = {"Fans": [{"Name": "fan1", "Reading": 7200, "ReadingUnits": "RPM"}], "PowerSupplies": [{"Name": "PSU1"}]}
        values = redfish_samples(data, {"origin": "live"})
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].name, "lab_redfish_fan_rpm")

    def test_rate_integration_uses_elapsed_time_and_retains_state(self):
        state = {}
        for stamp in (100, 102, 105):
            values = accumulate_rates([Sample("traffic_total", 20, {})], ["traffic_total"], state, now=stamp)
        self.assertEqual(values[0].value, 100)

    def test_failed_live_feed_is_not_replaced_with_simulation(self):
        with patch("lab.adapters.collect", side_effect=OSError("upstream unavailable")):
            runtime = Runtime({"dcgm": {"mode": "prometheus", "url": "http://example.invalid"}})
        try:
            self.assertFalse(runtime.up["dcgm"])
            self.assertEqual(runtime.samples["dcgm"], [])
            self.assertTrue(runtime.up["nim"])
            self.assertEqual(runtime.state()["origin"], "mixed")
        finally:
            runtime.executor.shutdown()


class DashboardContractTests(unittest.TestCase):
    def test_provisioned_dashboards_have_valid_unique_panel_ids_and_query_refs(self):
        root = Path(__file__).resolve().parents[1]
        types = set()
        for file in (root / "dashboards").glob("*.json"):
            board = json.loads(file.read_text())
            ids = [p["id"] for p in board["panels"]]
            self.assertEqual(len(ids), len(set(ids)))
            for panel in board["panels"]:
                types.add(panel["type"])
                for t in panel["targets"]:
                    self.assertIsInstance(t["refId"], str)
                    self.assertTrue(t["expr"])
                if panel["type"] == "marcusolsson-dynamictext-panel":
                    self.assertEqual(panel["options"]["renderMode"], "allRows")
                    self.assertEqual(panel["options"]["helpers"], "")
        self.assertIn("nodeGraph", types)
        self.assertIn("heatmap", types)
        self.assertIn("marcusolsson-dynamictext-panel", types)


if __name__ == "__main__":
    unittest.main()
