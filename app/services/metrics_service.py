"""
Metrics & Telemetry Service.
Tracks application counters, latency distributions, document ingestion, and retrieval statistics.
Exposes JSON and Prometheus metric endpoints.
"""

import time
from collections import defaultdict
from typing import Dict, Any

class MetricsService:
    def __init__(self):
        self.counters = defaultdict(int)
        self.latencies = defaultdict(list)

    def increment(self, metric_name: str, value: int = 1):
        """Increments a named counter."""
        self.counters[metric_name] += value

    def record_latency(self, metric_name: str, duration_ms: float):
        """Records an execution latency observation in milliseconds."""
        self.latencies[metric_name].append(round(duration_ms, 2))
        # Keep last 1000 observations per metric to manage memory
        if len(self.latencies[metric_name]) > 1000:
            self.latencies[metric_name] = self.latencies[metric_name][-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Returns structured JSON summary of metrics."""
        latency_stats = {}
        for name, values in self.latencies.items():
            if values:
                sorted_vals = sorted(values)
                count = len(sorted_vals)
                avg = sum(sorted_vals) / count
                p50 = sorted_vals[int(count * 0.50)]
                p95 = sorted_vals[min(int(count * 0.95), count - 1)]
                latency_stats[name] = {
                    "count": count,
                    "avg_ms": round(avg, 2),
                    "p50_ms": round(p50, 2),
                    "p95_ms": round(p95, 2)
                }

        return {
            "status": "healthy",
            "counters": dict(self.counters),
            "latencies": latency_stats
        }

    def get_prometheus_metrics(self) -> str:
        """Returns metrics formatted in standard Prometheus exposition format."""
        lines = []
        for name, val in self.counters.items():
            safe_name = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {safe_name} counter")
            lines.append(f"{safe_name} {val}")

        for name, values in self.latencies.items():
            if values:
                safe_name = name.replace(".", "_").replace("-", "_")
                avg = sum(values) / len(values)
                lines.append(f"# TYPE {safe_name}_avg_ms gauge")
                lines.append(f"{safe_name}_avg_ms {round(avg, 2)}")

        return "\n".join(lines) + "\n"

metrics_service = MetricsService()
