"""
n7x.models — canonical data structures.
Every field has: value, provenance (command), confidence, timestamp.
Fail-closed: missing data = INSUFFICIENT_EVIDENCE, not 0.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Confidence(str, Enum):
    HIGH   = "HIGH"    # exact API data, verified
    MEDIUM = "MEDIUM"  # sampled or derived
    LOW    = "LOW"     # estimated or inferred
    NONE   = "NONE"    # INSUFFICIENT_EVIDENCE


@dataclass
class Metric:
    """Single measurement with full provenance."""
    value: float | int | str | None
    unit: str
    provenance: str          # reproducible command/API call
    confidence: Confidence
    note: str = ""

    def is_valid(self) -> bool:
        return self.value is not None and self.confidence != Confidence.NONE


@dataclass
class DebtSignal:
    """Single debt signal: measured, scored, explained."""
    name: str
    category: str            # ACCUMULATION | DECAY | ISOLATION | HYGIENE | STABILITY
    raw: Metric
    debt_contribution: float  # 0–100, higher = more debt
    severity: str             # CRITICAL | HIGH | MEDIUM | LOW | OK
    finding: str              # human-readable explanation
    remediation: str          # what to do


@dataclass
class RepoSnapshot:
    """Full per-repo state at one point in time."""
    name: str
    url: str
    collected_at: str
    window_days: int
    signals: list[DebtSignal] = field(default_factory=list)
    debt_score: float = 0.0
    debt_level: str = ""
    # raw metrics (all with provenance)
    metrics: dict[str, Metric] = field(default_factory=dict)


@dataclass
class AccountSnapshot:
    """Full account state at one point in time."""
    handle: str
    collected_at: str
    window_days: int
    account_age_days: int = 0
    repos: list[RepoSnapshot] = field(default_factory=list)
    global_metrics: dict[str, Metric] = field(default_factory=dict)
    global_signals: list[DebtSignal] = field(default_factory=list)
    # scores
    total_debt_score: float = 0.0
    debt_level: str = "INSUFFICIENT_EVIDENCE"
    gcei_score: float = 0.0
    gcei_level: str = "INSUFFICIENT_EVIDENCE"
    confidence: Confidence = Confidence.NONE
    # deltas vs previous run
    debt_delta: float | None = None      # positive = debt grew
    gcei_delta: float | None = None      # positive = improvement
    # risks
    risk_sustainability: str = ""
    risk_accumulation: str = ""
    risk_isolation: str = ""
    risk_stability: str = ""
    # benchmarks
    benchmarks: dict[str, Any] = field(default_factory=dict)
    hard_caps: list[str] = field(default_factory=list)
    anti_gaming_penalties: list[str] = field(default_factory=list)
