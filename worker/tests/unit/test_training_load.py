import math
import pytest
from analytics.training_load import hr_tss, atl, ctl, tsb, decay_load


def test_hr_tss_basic():
    # 1 hour at threshold (IF=1.0) = 100 TSS
    result = hr_tss(duration_secs=3600, avg_hr=150, threshold_hr=150)
    assert abs(result - 100.0) < 0.01


def test_hr_tss_below_threshold():
    # 1 hour at 75% threshold = 56.25 TSS
    result = hr_tss(duration_secs=3600, avg_hr=112.5, threshold_hr=150)
    assert abs(result - 56.25) < 0.01


def test_hr_tss_invalid_threshold():
    with pytest.raises(ValueError):
        hr_tss(duration_secs=3600, avg_hr=150, threshold_hr=0)


def test_atl_decay_with_zero_tss():
    # ATL decays by exp(-1/7) each day with no load
    prev = 50.0
    result = atl(prev, tss=0.0)
    assert abs(result - prev * math.exp(-1 / 7)) < 0.001


def test_ctl_decay_with_zero_tss():
    prev = 80.0
    result = ctl(prev, tss=0.0)
    assert abs(result - prev * math.exp(-1 / 42)) < 0.001


def test_atl_converges():
    # After 7 days of constant TSS, ATL should be close to steady state
    constant_tss = 60.0
    load = 0.0
    for _ in range(28):
        load = atl(load, tss=constant_tss)
    # Steady state ≈ TSS (fully converged)
    assert abs(load - constant_tss) < 5.0


def test_tsb_is_ctl_minus_atl():
    assert tsb(ctl_value=80.0, atl_value=90.0) == pytest.approx(-10.0)
    assert tsb(ctl_value=90.0, atl_value=80.0) == pytest.approx(10.0)
