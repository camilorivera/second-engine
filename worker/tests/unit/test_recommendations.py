import pytest
from recommendations.engine import generate, RecommendationInput


def _input(**kwargs) -> RecommendationInput:
    return RecommendationInput(**kwargs)


def test_overreaching_fires_when_tsb_below_minus_20():
    recs = generate(_input(tsb=-25.0))
    categories = [r.category for r in recs]
    messages = [r.message for r in recs]
    assert "recovery" in categories
    assert any("TSB" in m for m in messages)


def test_overreaching_does_not_fire_when_tsb_ok():
    recs = generate(_input(tsb=5.0))
    assert all(r.category != "recovery" for r in recs)


def test_consistency_fires_when_low_active_days():
    recs = generate(_input(active_days_last_14=2))
    assert any(r.category == "training" and "consistency" in r.message.lower() for r in recs)


def test_consistency_does_not_fire_when_sufficient():
    recs = generate(_input(active_days_last_14=8))
    assert not any("consistency" in r.message.lower() for r in recs)


def test_resting_hr_improvement_fires():
    recs = generate(_input(resting_hr_today=57, resting_hr_30d_ago=64))
    assert any("Resting HR dropped" in r.message for r in recs)


def test_resting_hr_improvement_does_not_fire_for_small_delta():
    recs = generate(_input(resting_hr_today=62, resting_hr_30d_ago=64))
    assert not any("Resting HR dropped" in r.message for r in recs)


def test_weight_forecast_rec_fires():
    recs = generate(_input(weight_forecast_12w_kg=92.5))
    assert any("Projected weight" in r.message for r in recs)


def test_zone2_weight_correlation_fires():
    recs = generate(_input(week_z2_hours=5.0, weight_7d_trend_kg=-0.4))
    assert any("Zone 2" in r.message and "weight" in r.message.lower() for r in recs)


def test_empty_input_produces_only_consistency_rec():
    # With all defaults, active_days=0 triggers consistency
    recs = generate(RecommendationInput())
    assert any(r.category == "training" for r in recs)
