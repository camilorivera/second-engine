import pytest
from analytics.hr_zones import karvonen, HRZones


def test_karvonen_basic():
    zones = karvonen(max_hr=175, resting_hr=57)
    assert isinstance(zones, HRZones)
    assert zones.max_hr == 175
    assert zones.resting_hr == 57


def test_karvonen_zone_ordering():
    zones = karvonen(max_hr=175, resting_hr=57)
    assert zones.z1_min < zones.z1_max
    assert zones.z1_max == zones.z2_min
    assert zones.z2_max == zones.z3_min
    assert zones.z3_max == zones.z4_min
    assert zones.z4_max == zones.z5_min
    assert zones.z5_max == 175


def test_karvonen_z2_within_bounds():
    zones = karvonen(max_hr=180, resting_hr=60)
    assert zones.z2_min > zones.z1_max or zones.z2_min == zones.z1_max
    assert zones.z2_max < zones.z3_max


def test_karvonen_known_values():
    # HRR = 175 - 57 = 118
    # Z2 = 57 + 0.60*118=127.8 -> 128  to  57 + 0.70*118=139.6 -> 140
    zones = karvonen(max_hr=175, resting_hr=57)
    assert zones.z2_min == round(57 + 0.60 * 118)
    assert zones.z2_max == round(57 + 0.70 * 118)


def test_karvonen_raises_when_max_equals_resting():
    with pytest.raises(ValueError):
        karvonen(max_hr=60, resting_hr=60)


def test_karvonen_raises_when_max_less_than_resting():
    with pytest.raises(ValueError):
        karvonen(max_hr=55, resting_hr=60)
