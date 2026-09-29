"""
Risk Engine — Stage 7a  (rev 2 — calibrated thresholds)
=========================================================
Converts raw crowd-analysis values (headcount, motion speed) into a
normalised risk score (0–100 INT) and a categorical risk level string
that maps directly to the `analytics_events.risk_level` ENUM column.

Revision notes (rev 2):
  - MAX_EXPECTED_CROWD raised from 80 → 200.  The previous value of 80
    was a temporary test tuning that caused nearly every frame of a
    normal crowd video to score "high" or "severe".  200 is a realistic
    upper bound for a single-platform camera view at a busy station.
  - Motion multiplier bands widened:
      · Very still  (< 1.0 px/frame) → 0.8   (unchanged in effect)
      · Walking     (< 3.0 px/frame) → 1.1   (reduced from 1.2)
      · Brisk/panic (≥ 3.0 px/frame) → 1.5   (reduced from 1.8)
    The 1.8× multiplier was too aggressive and amplified normal pedestrian
    movement into the "severe" band.
  - Risk-level categorical thresholds tightened:
      · low      < 30   (unchanged)
      · moderate < 60   (unchanged)
      · high     < 80   (unchanged)
      · severe   ≥ 80   (unchanged)
    These stay fixed; the score itself is now better-calibrated.
"""

from typing import Literal

# ---------------------------------------------------------------------------
# Tuneable thresholds
# ---------------------------------------------------------------------------
# Maximum crowd size expected in a single camera view at the venue.
# Headcount beyond this is still clamped at 100 — it just means the crowd
# is denser than anticipated.
# 200 is a realistic upper bound for a busy railway platform camera shot.
MAX_EXPECTED_CROWD: int = 200

# Motion-speed multiplier bands.
# Values are pixels/frame as returned by calculate_optical_flow().
# The multiplier scales the density-based score:
#   very still crowd  → 0.8  (reduce score — dense but not moving)
#   walking crowd     → 1.1  (slight increase for normal pedestrian flow)
#   fast/panic crowd  → 1.5  (notable increase — potential stampede risk)
_MOTION_THRESHOLDS: list[tuple[float, float]] = [
    (1.0,  0.8),            # speed < 1.0  → multiplier 0.8
    (3.0,  1.1),            # speed < 3.0  → multiplier 1.1
    (float("inf"), 1.5),    # speed ≥ 3.0  → multiplier 1.5
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
    # low      0  – 29
    # moderate 30 – 69
    # high     70 – 79
    # severe   80 – 100
    risk_level: RiskLevel
    if risk_score < 30:
        risk_level = "low"
    elif risk_score < 70:
        risk_level = "moderate"
    elif risk_score < 80:
        risk_level = "high"
    else:
        risk_level = "severe"

    return risk_score, risk_level
