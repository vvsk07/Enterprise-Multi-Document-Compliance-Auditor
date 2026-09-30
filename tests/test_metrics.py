"""
Tests for Workstream 10: Metrics and Prometheus Export.
"""

import pytest
from app.services.metrics_service import MetricsService

def test_metrics_service_counters():
    service = MetricsService()
    service.increment("requests_total")
    service.increment("requests_total")
    service.increment("documents_ingested", 3)

    m = service.get_metrics()
    assert m["counters"]["requests_total"] == 2
    assert m["counters"]["documents_ingested"] == 3

def test_metrics_service_latency():
    service = MetricsService()
    service.record_latency("search_latency", 12.5)
    service.record_latency("search_latency", 25.0)

    m = service.get_metrics()
    assert "search_latency" in m["latencies"]
    assert m["latencies"]["search_latency"]["count"] == 2
    assert m["latencies"]["search_latency"]["avg_ms"] == 18.75

def test_prometheus_formatting():
    service = MetricsService()
    service.increment("search_requests", 5)
    prom_str = service.get_prometheus_metrics()
    assert "search_requests 5" in prom_str
