from dataclasses import dataclass
from typing import List, Tuple
from .states import MissionState


@dataclass(frozen=True)
class MissionSegment:
    state: MissionState
    duration_hours: float


@dataclass(frozen=True)
class LEOProfile:
    altitude_km: float
    inclination_deg: float


@dataclass(frozen=True)
class RiskConfig:
    n_sims: int
    dt_minutes: float
    leo: LEOProfile
    segments: List[MissionSegment]


def default_risk_config() -> RiskConfig:
    return RiskConfig(
        n_sims=1000,
        dt_minutes=5.0,
        leo=LEOProfile(altitude_km=700.0, inclination_deg=98.0),  # LEO/SSO-ish placeholder
        segments=[
            MissionSegment(MissionState.TRANSIT, 24),
            MissionSegment(MissionState.SEARCH, 48),
            MissionSegment(MissionState.PROXIMITY, 6),
            MissionSegment(MissionState.CAPTURE, 1),
            MissionSegment(MissionState.TOW, 24),
        ],
    )
