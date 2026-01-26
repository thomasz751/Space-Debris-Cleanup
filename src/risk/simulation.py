from dataclasses import dataclass
from typing import Dict
import random

from .config import RiskConfig
from .states import MissionState, VehicleStateParams, default_vehicle_params_by_state


@dataclass
class SimResult:
    outcome: str
    loss: float
    debris_hits: int
    conjunctions: int
    capture_attempted: bool


def debris_flux_rate_per_hour(alt_km: float, inc_deg: float) -> float:
    # STUB: replace later with altitude-band + size-bin model
    # For now: a small constant hazard that increases with altitude a bit
    return 1e-6 * (1.0 + (alt_km - 400.0) / 800.0)


def conjunction_rate_per_hour(alt_km: float, inc_deg: float) -> float:
    # STUB: replace later with a traffic model
    return 5e-7 * (1.0 + (alt_km - 400.0) / 800.0)


def run_one_mission(cfg: RiskConfig, params_by_state: Dict[MissionState, VehicleStateParams]) -> SimResult:
    dt_hr = cfg.dt_minutes / 60.0

    debris_hits = 0
    conjunctions = 0
    capture_attempted = False
    catastrophic = False

    # toy loss components (stub)
    loss = 0.0

    for seg in cfg.segments:
        steps = int(seg.duration_hours / dt_hr)
        p = params_by_state[seg.state]

        for _ in range(steps):
            # Channel A: debris flux (Poisson approx via Bernoulli for small dt)
            lam_d = debris_flux_rate_per_hour(cfg.leo.altitude_km, cfg.leo.inclination_deg) * p.area_bus_m2 * p.deploy_area_multiplier
            if random.random() < lam_d * dt_hr:
                debris_hits += 1
                # stub severity: small chance catastrophic
                if random.random() < 0.01:
                    catastrophic = True

            # Channel B: tracked conjunctions (event rate)
            lam_c = conjunction_rate_per_hour(cfg.leo.altitude_km, cfg.leo.inclination_deg)
            if random.random() < lam_c * dt_hr:
                conjunctions += 1
                # stub: attempt avoidance; otherwise small collision chance
                if random.random() > p.avoid_success_prob:
                    if random.random() < 1e-3:
                        catastrophic = True

            # Channel C: capture attempt happens during capture state (once)
        if seg.state == MissionState.CAPTURE and not catastrophic:
            capture_attempted = True
            # simple outcome tree
            if random.random() < p.capture_catastrophe_prob:
                catastrophic = True
            else:
                if random.random() < p.capture_success_prob:
                    pass  # success
                else:
                    # failed capture -> maybe damage/abort
                    loss += 1e5

        if catastrophic:
            break

    if catastrophic:
        outcome = "CATASTROPHIC"
        loss += 5e7  # placeholder replacement cost
    else:
        outcome = "COMPLETED"
        loss += 2e6  # placeholder mission cost

    return SimResult(outcome, loss, debris_hits, conjunctions, capture_attempted)


def run_simulation(cfg: RiskConfig) -> list[SimResult]:
    params_by_state = default_vehicle_params_by_state()
    return [run_one_mission(cfg, params_by_state) for _ in range(cfg.n_sims)]
