"""Small Prometheus text renderer and parser; no third-party runtime dependencies."""
import math
import re
from dataclasses import dataclass, field
from .catalog import SIGNALS

@dataclass
class Sample:
    name: str
    value: float
    labels: dict = field(default_factory=dict)

def escape(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

def labels_text(labels):
    return "{" + ",".join(f'{k}="{escape(v)}"' for k, v in sorted(labels.items())) + "}" if labels else ""

def render(samples, timestamp=None, openmetrics=False):
    metadata = {s["name"]: s for s in SIGNALS}
    lines, seen = [], set()
    for sample in samples:
        family = re.sub(r"_(bucket|sum|count)$", "", sample.name) if sample.name.endswith(("_bucket", "_sum", "_count")) else sample.name
        if family not in seen:
            spec = metadata.get(family, {})
            lines += [f'# HELP {family} {spec.get("meaning", "Lab observability signal.")}', f'# TYPE {family} {spec.get("type", "gauge")}']
            seen.add(family)
        value = "+Inf" if sample.value == math.inf else str(sample.value)
        stamp = f" {timestamp:.3f}" if timestamp is not None else ""
        lines.append(f"{sample.name}{labels_text(sample.labels)} {value}{stamp}")
    if openmetrics:
        lines.append("# EOF")
    return "\n".join(lines) + "\n"

LINE = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(.*)\})?\s+([^\s]+)(?:\s+[^\s]+)?$')
LABEL = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\.|[^"\\])*)"')

def parse(text, static_labels=None, rename=None):
    import json
    samples = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        match = LINE.match(line)
        if not match:
            continue
        name, labels, value = match.groups()
        try:
            number = float(value)
        except ValueError:
            continue
        if not math.isfinite(number):
            continue
        decoded = {k: json.loads('"' + v + '"') for k, v in LABEL.findall(labels or "")}
        decoded.update(static_labels or {})
        mapped = (rename or {}).get(name)
        if mapped is None:
            mapped = name
            for original, new in (rename or {}).items():
                if name in (original + "_bucket", original + "_sum", original + "_count"):
                    mapped = new + name[len(original):]
                    break
        samples.append(Sample(mapped, number, decoded))
    return samples
