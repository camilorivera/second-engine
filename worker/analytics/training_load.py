"""
ATL/CTL/TSB training load calculations using HR-based TSS.
Phase 2 implementation target.
"""
import math


def hr_tss(duration_secs: float, avg_hr: float, threshold_hr: float) -> float:
    """Calculate Training Stress Score from heart rate data."""
    if threshold_hr <= 0:
        raise ValueError("threshold_hr must be > 0")
    intensity_factor = avg_hr / threshold_hr
    duration_hours = duration_secs / 3600.0
    return duration_hours * (intensity_factor ** 2) * 100.0


def decay_load(previous: float, tss: float, time_constant: int) -> float:
    """Exponential decay update for ATL or CTL."""
    k = math.exp(-1.0 / time_constant)
    return previous * k + tss * (1.0 - k)


def atl(previous_atl: float, tss: float) -> float:
    """Acute Training Load (7-day decay)."""
    return decay_load(previous_atl, tss, 7)


def ctl(previous_ctl: float, tss: float) -> float:
    """Chronic Training Load (42-day decay)."""
    return decay_load(previous_ctl, tss, 42)


def tsb(ctl_value: float, atl_value: float) -> float:
    """Training Stress Balance = form/freshness."""
    return ctl_value - atl_value
