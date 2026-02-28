"""
PromptShield Gateway — Threat Logger
In-memory + JSON file logging for dashboard analytics.
Thread-safe with periodic persistence.
"""
import json
import os
import threading
from datetime import datetime, timezone
from collections import defaultdict
from models.schemas import ThreatLogEntry, DashboardStats, ThreatLevel


class ThreatLogger:
    """Thread-safe threat logging with in-memory analytics and JSON persistence."""

    def __init__(self, log_file: str = "threat_log.json"):
        self._lock = threading.Lock()
        self._log_file = log_file
        self._entries: list[dict] = []
        self._stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "sanitized_requests": 0,
            "safe_requests": 0,
            "total_pii_detected": 0,
            "total_injections_detected": 0,
            "pii_types": defaultdict(int),
            "injection_patterns": defaultdict(int),
        }
        self._load_existing()

    def _load_existing(self):
        """Load existing log entries if available."""
        try:
            if os.path.exists(self._log_file):
                with open(self._log_file, "r") as f:
                    data = json.load(f)
                    self._entries = data.get("entries", [])
                    saved_stats = data.get("stats", {})
                    self._stats["total_requests"] = saved_stats.get("total_requests", 0)
                    self._stats["blocked_requests"] = saved_stats.get("blocked_requests", 0)
                    self._stats["sanitized_requests"] = saved_stats.get("sanitized_requests", 0)
                    self._stats["safe_requests"] = saved_stats.get("safe_requests", 0)
                    self._stats["total_pii_detected"] = saved_stats.get("total_pii_detected", 0)
                    self._stats["total_injections_detected"] = saved_stats.get("total_injections_detected", 0)
                    self._stats["pii_types"] = defaultdict(int, saved_stats.get("pii_types", {}))
                    self._stats["injection_patterns"] = defaultdict(int, saved_stats.get("injection_patterns", {}))
        except (json.JSONDecodeError, IOError):
            pass

    def _persist(self):
        """Write current state to JSON file."""
        try:
            with open(self._log_file, "w") as f:
                json.dump({
                    "entries": self._entries[-500:],  # Keep last 500 entries
                    "stats": {
                        **self._stats,
                        "pii_types": dict(self._stats["pii_types"]),
                        "injection_patterns": dict(self._stats["injection_patterns"]),
                    }
                }, f, indent=2, default=str)
        except IOError:
            pass

    def log(
        self,
        prompt: str,
        pii_count: int,
        pii_types: list[str],
        injection_score: int,
        threat_level: ThreatLevel,
        patterns: list[str],
        action: str,
    ):
        """Log a threat event."""
        with self._lock:
            # Create log entry
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_ip": "campus-portal",
                "prompt_preview": prompt[:80] + "..." if len(prompt) > 80 else prompt,
                "pii_count": pii_count,
                "injection_score": injection_score,
                "threat_level": threat_level.value,
                "patterns": patterns,
                "action": action,
            }
            self._entries.append(entry)

            # Update stats
            self._stats["total_requests"] += 1
            self._stats["total_pii_detected"] += pii_count
            if threat_level == ThreatLevel.BLOCKED:
                self._stats["blocked_requests"] += 1
            elif pii_count > 0 or threat_level == ThreatLevel.SUSPICIOUS:
                self._stats["sanitized_requests"] += 1
            else:
                self._stats["safe_requests"] += 1

            if patterns:
                self._stats["total_injections_detected"] += 1
                for p in patterns:
                    self._stats["injection_patterns"][p] += 1

            for pii_type in pii_types:
                self._stats["pii_types"][pii_type] += 1

            # Persist every 5 entries
            if len(self._entries) % 5 == 0:
                self._persist()

    def get_stats(self) -> DashboardStats:
        """Get aggregated dashboard statistics."""
        with self._lock:
            total = max(self._stats["total_requests"], 1)

            # Build timeline (last 24 entries grouped into hourly buckets)
            timeline = []
            recent = self._entries[-50:]
            for entry in recent:
                timeline.append({
                    "timestamp": entry["timestamp"],
                    "threat_level": entry["threat_level"],
                    "score": entry["injection_score"],
                })

            return DashboardStats(
                total_requests=self._stats["total_requests"],
                blocked_requests=self._stats["blocked_requests"],
                sanitized_requests=self._stats["sanitized_requests"],
                safe_requests=self._stats["safe_requests"],
                total_pii_detected=self._stats["total_pii_detected"],
                total_injections_detected=self._stats["total_injections_detected"],
                top_pii_types=dict(
                    sorted(self._stats["pii_types"].items(),
                           key=lambda x: x[1], reverse=True)[:10]
                ),
                top_injection_patterns=dict(
                    sorted(self._stats["injection_patterns"].items(),
                           key=lambda x: x[1], reverse=True)[:10]
                ),
                threat_timeline=timeline,
                block_rate_percent=round(
                    self._stats["blocked_requests"] / total * 100, 1
                ),
                avg_threat_score=round(
                    sum(e["injection_score"] for e in self._entries) / max(len(self._entries), 1), 1
                ),
            )

    def get_recent_threats(self, limit: int = 20) -> list[ThreatLogEntry]:
        """Get recent threat log entries."""
        with self._lock:
            entries = self._entries[-limit:]
            return [
                ThreatLogEntry(**entry)
                for entry in reversed(entries)
            ]

    def reset(self):
        """Reset all stats and entries (for testing)."""
        with self._lock:
            self._entries = []
            self._stats = {
                "total_requests": 0,
                "blocked_requests": 0,
                "sanitized_requests": 0,
                "safe_requests": 0,
                "total_pii_detected": 0,
                "total_injections_detected": 0,
                "pii_types": defaultdict(int),
                "injection_patterns": defaultdict(int),
            }
            self._persist()


# Singleton
threat_logger = ThreatLogger()
