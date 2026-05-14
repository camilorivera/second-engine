import pytest
from analytics.forecasting import linear_forecast, weight_forecast_kg, InsufficientDataError


def test_flat_series_forecasts_same_value():
    weights = [95.0] * 30
    result = linear_forecast(weights, forecast_days=84)
    assert abs(result - 95.0) < 0.5


def test_declining_trend():
    # 0.5 kg/week loss over 90 days = ~6.4 kg in 12 weeks
    # daily decline = 0.5/7 per day
    start = 100.0
    rate = 0.5 / 7
    weights = [start - rate * i for i in range(90)]
    result = weight_forecast_kg(weights, weeks_ahead=12)
    expected = start - rate * (90 + 84 - 1)
    assert abs(result - expected) < 1.0


def test_insufficient_data_raises():
    with pytest.raises(InsufficientDataError):
        linear_forecast([95.0, 94.5], forecast_days=10)


def test_single_point_raises():
    with pytest.raises(InsufficientDataError):
        linear_forecast([95.0], forecast_days=10)


def test_forecast_returns_float():
    weights = [95.0 - i * 0.05 for i in range(30)]
    result = weight_forecast_kg(weights, weeks_ahead=12)
    assert isinstance(result, float)
