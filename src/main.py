import numpy as np
import matplotlib.pyplot as plt

from src.simulation.mission_cycle import CycleParams
from src.simulation.monte_carlo import run_portfolio, MissionParams
from src.simulation.mission import AttemptParams
from src.simulation.loss import LossParams
from src.simulation.debris_environment import DebrisEnvParams




def var(x: np.ndarray, p: float) -> float:
    return float(np.quantile(x, p))

def tvar(x: np.ndarray, p: float) -> float:
    v = var(x, p)
    tail = x[x >= v]
    return float(tail.mean()) if tail.size else v

def main():
    n_sats = 10000
    seed = 42

    mission = MissionParams(years=3, attempts_per_year=40)
    env_params = DebrisEnvParams()
    cycle_params = CycleParams(env_params=env_params)
    loss_params = LossParams(insured_value=50_000_000.0)

    df = run_portfolio(n_sats, seed, mission, cycle_params, loss_params, env_params)
    losses = df["loss"].to_numpy()

    p = 0.99
    exp_loss = losses.mean()
    tv = tvar(losses, p)

    # simple pricing rule (you can swap later)
    expense_load = 0.10
    premium = tv * (1 + expense_load)

    print("=== Outcomes ===")
    print(df["ended"].value_counts(normalize=True))
    print("\n=== Loss Summary ===")
    print(f"E[Loss]:   {exp_loss:,.0f}")
    print(f"VaR({p}):  {var(losses, p):,.0f}")
    print(f"TVaR({p}): {tv:,.0f}")
    print("\n=== Premium (TVaR + 10% load) ===")
    print(f"Premium:   {premium:,.0f}")
    print("\nAvg D_end:", df["D_end"].mean())
    print("Avg mass_kg:", df["mass_kg"].mean())

    plt.figure()
    plt.hist(losses, bins=60)
    plt.title("Debris Cleanup Satellite – Simulated Loss Distribution")
    plt.xlabel("Loss ($)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig("loss_distribution.png", dpi=200)
    print("\nSaved: loss_distribution.png")

if __name__ == "__main__":
    main()

