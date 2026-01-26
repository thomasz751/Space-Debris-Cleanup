from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class MissionState(str, Enum):
    TRANSIT = "transit"
    SEARCH = "search"
    PROXIMITY = "proximity"
    CAPTURE = "capture"
    TOW = "tow"
    EVADE = "evade"
    SAFE_MODE = "safe_mode"


@dataclass(frozen=True)
class VehicleStateParams:
    # geometry knobs (design-agnostic)
    area_bus_m2: float
    deploy_area_multiplier: float  # e.g., 1.0 transit, >1.0 when deployed
    hbr_m: float  # hard-body radius proxy for conjunction Pc

    # ops knobs
    avoid_success_prob: float  # simplified for now

    # capture knobs (only meaningful in capture)
    capture_success_prob: float
    capture_catastrophe_prob: float


def default_vehicle_params_by_state() -> Dict[MissionState, VehicleStateParams]:
    # placeholder values — you'll tune later
    base_area = 4.0
    return {
        MissionState.TRANSIT: VehicleStateParams(base_area, 1.0, 1.5, 0.7, 0.0, 0.0),
        MissionState.SEARCH: VehicleStateParams(base_area, 1.0, 1.5, 0.7, 0.0, 0.0),
        MissionState.PROXIMITY: VehicleStateParams(base_area, 1.5, 1.7, 0.6, 0.0, 0.0),
        MissionState.CAPTURE: VehicleStateParams(base_area, 2.0, 2.0, 0.5, 0.6, 0.02),
        MissionState.TOW: VehicleStateParams(base_area, 2.5, 2.2, 0.5, 0.0, 0.0),
        MissionState.EVADE: VehicleStateParams(base_area, 1.0, 1.5, 0.9, 0.0, 0.0),
        MissionState.SAFE_MODE: VehicleStateParams(base_area, 1.0, 1.5, 0.2, 0.0, 0.0),
    }
