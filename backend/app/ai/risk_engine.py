"""
Risk Engine — Stage 7a
======================
Converts raw crowd-analysis values (headcount, motion speed) into a
normalised risk score (0–100 INT) and a categorical risk level string
that maps directly to the `analytics_events.risk_level` ENUM column.
"""

from typing import Literal

# ---------------------------------------------------------------------------
# Tuneable thresholds
# ---------------------------------------------------------------------------
# Maximum crowd size expected at the venue.  Headcount beyond this is still
# clamped at 100 — it just means the crowd is denser than anticipated.
MAX_EXPECTED_CROWD: int = 500

# Motion-speed multiplier bands.
# Values are pixels/frame as returned by calculate_optical_flow().
# The multiplier scales the density-based score:
#   very still crowd  → 0.5  (reduce score — dense but not moving)
#   walking crowd     → 1.0  (neutral)
#   fast-moving crowd → 1.5  (increase score — stampede risk)
_MOTION_THRESHOLDS: list[tuple[float, float]] = [
    (0.5,  0.5),   # speed < 0.5  → multiplier 0.5
    (2.0,  1.0),   # speed < 2.0  → multiplier 1.0
    (float("inf"), 1.5),  # speed ≥ 2.0  → multiplier 1.5
]

RiskLevel = Literal["low", "moderate", "high", "severe"]


def _motion_multiplier(motion_speed: float) -> float:
    """Return a scaling factor based on the average optical-flow magnitude."""
    for threshold, multiplier in _MOTION_THRESHOLDS:
        if motion_speed < threshold:
            return multiplier
    return 1.5  # fallback (should never be reached)


def calculate_risk(
    headcount: int,
    motion_speed: float,
) -> tuple[int, RiskLevel]:
    """
    Compute a crowd risk score and categorical risk level.

    Formula:
        raw_score = (headcount / MAX_EXPECTED_CROWD) * 100 * motion_multiplier
        risk_score = clamp(round(raw_score), 0, 100)

    Args:
        headcount:    Estimated number of people in the frame (from CSRNet).
        motion_speed: Average optical-flow magnitude (from calculate_optical_flow).

    Returns:
        risk_score (int):   Clamped integer in [0, 100].
        risk_level (str):   One of 'low', 'moderate', 'high', 'severe'.
    """
    multiplier = _motion_multiplier(motion_speed)

    raw_score = (headcount / MAX_EXPECTED_CROWD) * 100.0 * multiplier

    # Clamp to [0, 100] and round to the nearest integer.
    risk_score: int = int(max(0, min(100, round(raw_score))))

    # Categorical threshold mapping.
    risk_level: RiskLevel
    if risk_score < 30:
        risk_level = "low"
    elif risk_score < 60:
        risk_level = "moderate"
    elif risk_score < 80:
        risk_level = "high"
    else:
        risk_level = "severe"

    return risk_score, risk_level
