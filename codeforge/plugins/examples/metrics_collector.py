"""[7.13] Plugin: Add example metrics collector plugin."""

import time
from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._start_time = time.time()

    def increment(self, metric_name: str, value: int = 1) -> None:
        self._counters[metric_name] += value

    def record_timing(self, name: str, duration_ms: float) -> None:
        self._timers[name].append(duration_ms)

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_timings(self) -> dict[str, dict]:
        return {
            name: {
                "count": len(times),
                "avg_ms": sum(times) / len(times) if times else 0,
                "min_ms": min(times) if times else 0,
                "max_ms": max(times) if times else 0,
            }
            for name, times in self._timers.items()
        }

    def get_uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def get_summary(self) -> dict:
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "counters": self.get_counters(),
            "timings": self.get_timings(),
        }
