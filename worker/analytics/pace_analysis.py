"""
Pace and aerobic efficiency analytics.
Phase 3 implementation target.
"""


def hr_drift_pct(hr_stream: list[int]) -> float | None:
    """
    Calculate cardiac drift as % HR increase from first to second half.
    Positive = drift (fatigue). Improving over time = adaptation.
    """
    if len(hr_stream) < 10:
        return None
    mid = len(hr_stream) // 2
    first_half = [h for h in hr_stream[:mid] if h]
    second_half = [h for h in hr_stream[mid:] if h]
    if not first_half or not second_half:
        return None
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    return (avg_second - avg_first) / avg_first * 100.0


def pace_at_zone(
    hr_stream: list[int],
    pace_stream: list[float],
    zone_min: int,
    zone_max: int,
) -> float | None:
    """
    Average pace (seconds/km) during stream points where HR is within the zone.
    Returns None if no qualifying data points.
    """
    qualifying = [
        pace_stream[i]
        for i, hr in enumerate(hr_stream)
        if i < len(pace_stream) and hr and zone_min <= hr <= zone_max and pace_stream[i]
    ]
    if not qualifying:
        return None
    return sum(qualifying) / len(qualifying)
