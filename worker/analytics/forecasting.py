"""
Linear regression forecasting for weight and pace trends.
Phase 4 implementation target.
"""
from scipy.stats import linregress


class InsufficientDataError(ValueError):
    pass


def linear_forecast(values: list[float], forecast_days: int, min_points: int = 7) -> float:
    """
    Project a future value using linear regression over the provided series.
    values: chronologically ordered measurements (one per day or per week).
    forecast_days: how many steps ahead to project.
    Returns the projected value.
    """
    if len(values) < min_points:
        raise InsufficientDataError(
            f"Need at least {min_points} data points, got {len(values)}"
        )

    x = list(range(len(values)))
    slope, intercept, _, _, _ = linregress(x, values)
    return intercept + slope * (len(values) - 1 + forecast_days)


def weight_forecast_kg(weights_90d: list[float], weeks_ahead: int = 12) -> float:
    """Project weight in kg N weeks ahead from recent 90-day trend."""
    return linear_forecast(weights_90d, forecast_days=weeks_ahead * 7)


def pace_forecast_spm(weekly_pace_at_z2: list[float], weeks_ahead: int = 12) -> float:
    """Project pace at Zone 2 (seconds/km) N weeks ahead."""
    return linear_forecast(weekly_pace_at_z2, forecast_days=weeks_ahead)
