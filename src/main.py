import numpy as np
import matplotlib.pyplot as plt

from src.simulation.monte_carlo import run_portfolio, MissionParams
from src.simulation.mission import AttemptParams
from src.simulation.loss import LossParams

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
    attempt = AttemptParams(p_success=0.94, p_abort=0.05, p_catastrophic=0.01)
    loss_params = LossParams(insured_value=50_000_000.0)

    df = run_portfolio(n_sats, seed, mission, attempt, loss_params)
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

