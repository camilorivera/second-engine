"""
Weight smoothing and trend analysis.
Phase 3 implementation target.
"""


def rolling_average(values: list[float], window: int = 7) -> list[float | None]:
    """Calculate rolling mean with given window. Returns None for positions with insufficient data."""
    result: list[float | None] = []
    for i, _ in enumerate(values):
        if i < window - 1:
            result.append(None)
        else:
            window_vals = [v for v in values[i - window + 1: i + 1] if v is not None]
            result.append(sum(window_vals) / len(window_vals) if window_vals else None)
    return result


def weekly_average(daily_weights: list[float | None]) -> list[float]:
    """Collapse daily weights into weekly averages, ignoring None values."""
    weeks: list[float] = []
    for chunk_start in range(0, len(daily_weights), 7):
        chunk = [v for v in daily_weights[chunk_start:chunk_start + 7] if v is not None]
        if chunk:
            weeks.append(sum(chunk) / len(chunk))
    return weeks
