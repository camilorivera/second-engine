"""
Rule-based recommendation engine.
Phase 4 implementation target — stubs present for test scaffolding.
"""
from dataclasses import dataclass, field


@dataclass
class RecommendationInput:
    week_z2_hours: float = 0.0
    weight_7d_trend_kg: float = 0.0
    resting_hr_today: int | None = None
    resting_hr_30d_ago: int | None = None
    pace_at_z2_today_spm: float | None = None
    pace_at_z2_90d_ago_spm: float | None = None
    tsb: float | None = None
    active_days_last_14: int = 0
    weight_forecast_12w_kg: float | None = None


@dataclass
class Recommendation:
    category: str
    message: str
    supporting_data: dict = field(default_factory=dict)


def generate(data: RecommendationInput) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if data.week_z2_hours >= 4 and data.weight_7d_trend_kg < 0:
        recs.append(Recommendation(
            category="weight",
            message="Weeks with 4+ hours in Zone 2 correlate with your best weight-loss trend.",
            supporting_data={"week_z2_hours": data.week_z2_hours, "weight_7d_trend_kg": data.weight_7d_trend_kg},
        ))

    if data.resting_hr_today and data.resting_hr_30d_ago:
        delta = data.resting_hr_30d_ago - data.resting_hr_today
        if delta >= 3:
            recs.append(Recommendation(
                category="training",
                message=f"Resting HR dropped {delta} bpm over 30 days — clear cardiovascular adaptation.",
                supporting_data={"delta_bpm": delta},
            ))

    if data.pace_at_z2_today_spm and data.pace_at_z2_90d_ago_spm:
        improvement = (data.pace_at_z2_90d_ago_spm - data.pace_at_z2_today_spm) / data.pace_at_z2_90d_ago_spm
        if improvement >= 0.05:
            recs.append(Recommendation(
                category="pace",
                message=f"Zone 2 pace improved {improvement * 100:.0f}% over 90 days.",
                supporting_data={"improvement_pct": round(improvement * 100, 1)},
            ))

    if data.tsb is not None and data.tsb < -20:
        recs.append(Recommendation(
            category="recovery",
            message=f"High fatigue detected (TSB = {data.tsb:.0f}). Consider an easy week.",
            supporting_data={"tsb": data.tsb},
        ))

    if data.active_days_last_14 < 4:
        recs.append(Recommendation(
            category="training",
            message=f"Low training consistency ({data.active_days_last_14} sessions in 14 days). Aim for 4+ per week.",
            supporting_data={"active_days": data.active_days_last_14},
        ))

    if data.weight_forecast_12w_kg is not None:
        recs.append(Recommendation(
            category="weight",
            message=f"Projected weight in 12 weeks: {data.weight_forecast_12w_kg:.1f} kg at current trend.",
            supporting_data={"forecast_kg": data.weight_forecast_12w_kg},
        ))

    return recs
