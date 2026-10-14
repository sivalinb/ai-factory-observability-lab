#!/usr/bin/env python3
"""Optional real PyTorch toy-token training; NCCL on CUDA, Gloo on CPU."""
import argparse
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.metrics import Sample, render


class MetricsHandler(BaseHTTPRequestHandler):
    snapshot = []
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        data = render(self.snapshot).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--sequence", type=int, default=128)
    parser.add_argument("--workload", default="train-42")
    parser.add_argument("--node", default=socket.gethostname())
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--slow-rank", type=int, default=-1)
    parser.add_argument("--delay-ms", type=float, default=50)
    parser.add_argument("--baseline", type=float, help="Healthy tokens/s reference; otherwise derived after 20 warmup steps")
    args = parser.parse_args()
    try:
        import torch
        import torch.distributed as dist
        from torch.nn.parallel import DistributedDataParallel
    except ImportError:
        raise SystemExit("Install a supported PyTorch build from https://pytorch.org/get-started/locally/ for this optional workload.")
    world = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    cuda = torch.cuda.is_available() if args.device == "auto" else args.device == "cuda"
    if cuda:
        torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank) if cuda else torch.device("cpu")
    if world > 1:
        dist.init_process_group("nccl" if cuda else "gloo")
    model = torch.nn.Sequential(torch.nn.Linear(128, 512), torch.nn.GELU(), torch.nn.Linear(512, 32)).to(device)
    if world > 1:
        model = DistributedDataParallel(model, device_ids=[local_rank] if cuda else None)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
    inputs = torch.randn(args.batch, args.sequence, 128, device=device)
    targets = torch.randint(0, 32, (args.batch * args.sequence,), device=device)
    collective = torch.ones(262144, device=device)
    server = None
    if rank == 0:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), MetricsHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Real {device.type} training telemetry: http://localhost:{args.port}/metrics", flush=True)
    count, baseline, warmup = 0, args.baseline, []
    common = {"cluster": "factory-lab", "origin": "live", "source": "workload", "workload": args.workload}
    try:
        for step in range(args.steps):
            if cuda:
                torch.cuda.synchronize()
            started = time.perf_counter()
            optimizer.zero_grad()
            output = model(inputs).reshape(-1, 32)
            loss = torch.nn.functional.cross_entropy(output, targets)
            loss.backward()
            optimizer.step()
            collective_start = time.perf_counter()
            if rank == args.slow_rank:
                time.sleep(args.delay_ms / 1000)
            if world > 1:
                dist.all_reduce(collective)
            if cuda:
                torch.cuda.synchronize()
            collective_seconds = time.perf_counter() - collective_start
            duration = time.perf_counter() - started
            info = {"rank": str(rank), "node": args.node, "step": duration, "collective": collective_seconds}
            gathered = [None] * world
            if world > 1:
                dist.all_gather_object(gathered, info)
            else:
                gathered[0] = info
            if rank == 0:
                throughput = args.batch * args.sequence * world / max(g["step"] for g in gathered)
                if 5 <= step < 20:
                    warmup.append(throughput)
                if baseline is None and step >= 20:
                    baseline = sum(warmup) / len(warmup)
                count += args.batch * args.sequence * world
                snapshot = [Sample("lab_training_tokens_total", count, common)]
                if baseline is not None:
                    snapshot.append(Sample("lab_training_baseline_tokens_per_second", baseline, common))
                for item in gathered:
                    labels = {**common, "node": item["node"], "rank": item["rank"]}
                    snapshot += [Sample("lab_training_step_seconds", item["step"], labels), Sample("lab_nccl_collective_seconds", item["collective"], labels)]
                MetricsHandler.snapshot = snapshot
                if step % 100 == 0:
                    print(f"step={step} loss={loss.item():.3f} tokens/s={throughput:.0f}", flush=True)
    finally:
        if server:
            server.shutdown()
        if world > 1:
            dist.destroy_process_group()


if __name__ == "__main__":
    main()
