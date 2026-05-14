"""
Karvonen HR zone calculation and zone history storage.
Phase 2 implementation target.
"""
from dataclasses import dataclass


@dataclass
class HRZones:
    max_hr: int
    resting_hr: int
    z1_min: int
    z1_max: int
    z2_min: int
    z2_max: int
    z3_min: int
    z3_max: int
    z4_min: int
    z4_max: int
    z5_min: int
    z5_max: int


def karvonen(max_hr: int, resting_hr: int) -> HRZones:
    """Calculate 5-zone Karvonen HR zones from max and resting HR."""
    if max_hr <= resting_hr:
        raise ValueError(f"max_hr ({max_hr}) must be greater than resting_hr ({resting_hr})")

    hrr = max_hr - resting_hr

    def zone_bound(pct: float) -> int:
        return round(resting_hr + pct * hrr)

    return HRZones(
        max_hr=max_hr,
        resting_hr=resting_hr,
        z1_min=zone_bound(0.50),
        z1_max=zone_bound(0.60),
        z2_min=zone_bound(0.60),
        z2_max=zone_bound(0.70),
        z3_min=zone_bound(0.70),
        z3_max=zone_bound(0.80),
        z4_min=zone_bound(0.80),
        z4_max=zone_bound(0.90),
        z5_min=zone_bound(0.90),
        z5_max=max_hr,
    )
