import numpy as np
import pandas as pd
from dataclasses import dataclass
from .mission import AttemptParams, simulate_one_attempt
from .loss import LossParams, loss_for_attempt

@dataclass(frozen=True)
class MissionParams:
    years: int = 3
    attempts_per_year: int = 40  # cleanup attempts/year

def simulate_one_satellite(seed: int,
                           mission: MissionParams,
                           attempt: AttemptParams,
                           loss_params: LossParams) -> dict:
    rng = np.random.default_rng(seed)

    total_loss = 0.0
    successes = 0
    aborts = 0

    for _ in range(mission.years * mission.attempts_per_year):
        outcome = simulate_one_attempt(rng, attempt)
        total_loss += loss_for_attempt(rng, outcome, loss_params)

        if outcome == "SUCCESS":
            successes += 1
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
                  loss_params: LossParams) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seeds = rng.integers(0, 2**31 - 1, size=n_sats)
    rows = [simulate_one_satellite(int(s), mission, attempt, loss_params) for s in seeds]
    return pd.DataFrame(rows)
