from dataclasses import dataclass

import numpy as np
import pandas as pd

from .debris_environment import (
    DebrisEnvParams,
    OrbitState,
    update_density,
    catastrophic_prob_from_flux,
    scaled_catastrophic_prob,   # optional: keep for comparison
)

from .loss import LossParams, loss_for_attempt
from .mission import AttemptParams, simulate_one_attempt


@dataclass(frozen=True)
class MissionParams:
    years: int = 3
    attempts_per_year: int = 40  # cleanup attempts/year

def simulate_one_satellite(seed: int,
                           mission: MissionParams,
                           attempt: AttemptParams,
                           loss_params: LossParams,
                           env_params: DebrisEnvParams) -> dict:
    rng = np.random.default_rng(seed)
    D = env_params.D0
    D_history = []



    total_loss = 0.0
    successes = 0
    aborts = 0

    for year in range(mission.years):
        D_history.append(D)
        orbit = OrbitState(alt_km=700)
        p_cat_year = catastrophic_prob_from_flux(
            orbit=orbit,
            D=D,
            area_m2=10.0,
            duration_hours=2.0,
            params=env_params,
            direction="ram",
        )

        # new attempt params with catastrophic per year added in
        attempt_year = AttemptParams(
            p_success=attempt.p_success,
            p_abort=attempt.p_abort,
            p_catastrophic=p_cat_year
        )
        # initialize no removals yet
        removals_this_year = 0

        for _ in range(mission.attempts_per_year):
            outcome = simulate_one_attempt(rng, attempt_year)
            total_loss += loss_for_attempt(rng, outcome, loss_params)

            if outcome == "SUCCESS":
                successes += 1
                removals_this_year += 1
            elif outcome == "ABORT":
                aborts += 1
            elif outcome == "CATASTROPHIC":
                # mission ends immediately
                return {
                    "ended": "CATASTROPHIC",
                    "successes": successes,
                    "aborts": aborts,
                    "loss": total_loss
                }
        D = update_density(D, removals_this_year, env_params)

    # survived the full mission
    return {
        "ended": "COMPLETED",
        "successes": successes,
        "aborts": aborts,
        "loss": total_loss
    }

def run_portfolio(n_sats: int,
                  seed: int,
                  mission: MissionParams,
                  attempt: AttemptParams,
                  loss_params: LossParams,
                  env_params: DebrisEnvParams) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seeds = rng.integers(0, 2**31 - 1, size=n_sats)
    rows = [simulate_one_satellite(int(s), mission, attempt, loss_params, env_params) for s in seeds]
    return pd.DataFrame(rows)
