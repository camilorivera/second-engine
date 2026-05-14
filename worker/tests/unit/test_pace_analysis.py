import pytest
from analytics.pace_analysis import hr_drift_pct, pace_at_zone


def test_hr_drift_positive():
    # Second half HR higher than first
    first = [140] * 10
    second = [155] * 10
    drift = hr_drift_pct(first + second)
    assert drift is not None
    assert drift > 0


def test_hr_drift_zero():
    stream = [150] * 20
    drift = hr_drift_pct(stream)
    assert drift == pytest.approx(0.0, abs=0.01)


def test_hr_drift_insufficient_data():
    assert hr_drift_pct([140, 145]) is None


def test_pace_at_zone_filters_correctly():
    hr = [130, 140, 150, 160, 170]
    pace = [360.0, 340.0, 320.0, 300.0, 280.0]
    result = pace_at_zone(hr, pace, zone_min=135, zone_max=155)
    # Only hr=140 (pace=340) and hr=150 (pace=320) qualify
    assert result == pytest.approx((340.0 + 320.0) / 2)


def test_pace_at_zone_no_qualifying_returns_none():
    hr = [120, 125, 130]
    pace = [380.0, 375.0, 370.0]
    result = pace_at_zone(hr, pace, zone_min=150, zone_max=165)
    assert result is None
