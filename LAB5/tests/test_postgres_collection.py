from collections import Counter
import json

import pytest

from lab05_real_software import postgres_collection as collection


def test_block_order_is_balanced_and_reproducible():
    config = json.loads(collection.CONFIG.read_text(encoding="utf-8"))
    orders = collection.block_orders(config)
    versions = tuple(config["versions"])
    assert Counter(orders) == {versions: 12, versions[::-1]: 12}
    assert orders == collection.block_orders(config)


@pytest.mark.parametrize(("version", "output"), [
    ("1", "2000000\n20000000"),
    ("2", "usage_usec 2000\nuser_usec 1000\n20000000"),
])
def test_resource_counters_have_equal_units(monkeypatch, version, output):
    monkeypatch.setattr(collection, "docker", lambda *args: output)
    sample = collection.sample_resources("container", version)
    assert sample["cpu_usage_usec"] == 2000
    assert sample["memory_bytes"] == 20000000


def test_pgbench_metrics_use_the_resource_window():
    output = (
        "number of transactions actually processed: 500\n"
        "number of failed transactions: 0 (0.000%)\n"
        "latency average = 4.0 ms\n"
        "tps = 100.0 (without initial connection time)"
    )
    samples = [
        {"time_monotonic_seconds": 1, "cpu_usage_usec": 500_000, "memory_bytes": 10_000_000},
        {"time_monotonic_seconds": 6, "cpu_usage_usec": 3_000_000, "memory_bytes": 30_000_000},
    ]
    metrics = collection.summarize_load(output, samples, 1)
    assert metrics["throughput_queries_per_second"] == 100
    assert metrics["cpu_percent"] == 50
    assert metrics["memory_mb"] == 20
    assert metrics["client_latency_ms"] == 4
    with pytest.raises(ValueError, match="failed transactions"):
        collection.summarize_load(output.replace("failed transactions: 0", "failed transactions: 1"), samples, 1)
