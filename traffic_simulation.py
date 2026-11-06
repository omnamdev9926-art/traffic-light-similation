
"""
Smart Traffic Flow Simulation and Optimization
----------------------------------------------
Course : Solving Problems Through Modelling and Simulation

Model  : One 4-way intersection (North, South, East, West).
         Cars arrive randomly (Poisson process), wait in a queue, and leave
         when their road has a green signal.

We compare three signal controllers:
    1. Fixed-Time      : every road gets the same green time (normal traffic light)
    2. Optimized Fixed : best fixed green time, found by trying many values
    3. Smart Adaptive  : signal looks at queue length and adjusts green time

Time step = 1 second.

Run:   python traffic_simulation.py
Needs: pip install numpy matplotlib pandas
"""

import os
import random
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # save plots to files (works without a screen)
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# 1. PARAMETERS  (change these to experiment)
# ----------------------------------------------------------------------
SIM_TIME = 3600            # simulate 1 hour (seconds)
SERVICE_TIME = 2.0         # 1 car crosses every 2 s when green (saturation flow)
YELLOW_TIME = 3            # lost time (yellow + all-red) when signal changes
BASE_ARRIVAL = {"N": 0.12, "S": 0.12, "E": 0.09, "W": 0.09}   # cars/second
# Rush hour: demand rises between 20 and 40 minutes (x1.5)
RUSH_START, RUSH_END, RUSH_FACTOR = 1200, 2400, 1.5
REPLICATIONS = 20          # number of independent runs (for reliable averages)
OUT_DIR = "traffic_output"

APPROACHES = ["N", "S", "E", "W"]
PHASE_ROADS = {0: ["N", "S"], 1: ["E", "W"]}     # phase 0 = NS green, 1 = EW green


# ----------------------------------------------------------------------
# 2. SIGNAL CONTROLLERS
# ----------------------------------------------------------------------
class FixedController:
    """Same green time for both phases."""
    name = "Fixed-Time"

    def __init__(self, green=30):
        self.green = green

    def reset(self):
        pass

    def should_switch(self, t, time_in_green, queues, phase):
        return time_in_green >= self.green


class AdaptiveController:
    """
    Smart rule:
      - Always give at least MIN_GREEN seconds.
      - Never give more than MAX_GREEN seconds.
      - After MIN_GREEN: switch if the green road is (almost) empty
        OR the red roads have a much longer queue.
    """
    name = "Smart Adaptive"

    def __init__(self, min_green=10, max_green=60, ratio=1.5):
        self.min_green = min_green
        self.max_green = max_green
        self.ratio = ratio

    def reset(self):
        pass

    def should_switch(self, t, time_in_green, queues, phase):
        if time_in_green < self.min_green:
            return False
        if time_in_green >= self.max_green:
            return True
        green_q = sum(queues[r] for r in PHASE_ROADS[phase])
        red_q = sum(queues[r] for r in PHASE_ROADS[1 - phase])
        if green_q == 0 and red_q > 0:
            return True
        if red_q > self.ratio * max(green_q, 1) and red_q >= 4:
            return True
        return False


# ----------------------------------------------------------------------
# 3. SIMULATION
# ----------------------------------------------------------------------
@dataclass
class Result:
    avg_wait: float
    max_queue: int
    throughput: int
    left_in_queue: int
    queue_history: np.ndarray      # total cars waiting at each second


def arrival_rate(road, t):
    rate = BASE_ARRIVAL[road]
    if RUSH_START <= t < RUSH_END:
        rate *= RUSH_FACTOR
    return rate


def run_simulation(controller, seed):
    rng = random.Random(seed)
    controller.reset()

    queues = {r: [] for r in APPROACHES}      # each car stored as arrival time
    waits = []                                # waiting time of every car that left
    queue_history = np.zeros(SIM_TIME)

    phase = 0
    time_in_green = 0
    yellow_left = 0          # seconds of yellow remaining (nobody moves)
    service_credit = 0.0     # lets a car leave every SERVICE_TIME seconds

    for t in range(SIM_TIME):
        # --- (a) new cars arrive: probability = rate in each 1-second step
        for r in APPROACHES:
            if rng.random() < arrival_rate(r, t):
                queues[r].append(t)

        # --- (b) signal logic
        if yellow_left > 0:
            yellow_left -= 1
            if yellow_left == 0:
                phase = 1 - phase
                time_in_green = 0
                service_credit = 0.0
        else:
            q_len = {r: len(queues[r]) for r in APPROACHES}
            if controller.should_switch(t, time_in_green, q_len, phase):
                yellow_left = YELLOW_TIME
            else:
                # --- (c) cars leave on green
                service_credit += 1.0
                while service_credit >= SERVICE_TIME:
                    served_any = False
                    for r in PHASE_ROADS[phase]:
                        if queues[r]:
                            arrived = queues[r].pop(0)
                            waits.append(t - arrived)
                            served_any = True
                    service_credit -= SERVICE_TIME
                    if not served_any:
                        service_credit = 0.0
                        break
                time_in_green += 1

        queue_history[t] = sum(len(queues[r]) for r in APPROACHES)

    left = int(queue_history[-1])
    return Result(
        avg_wait=float(np.mean(waits)) if waits else 0.0,
        max_queue=int(queue_history.max()),
        throughput=len(waits),
        left_in_queue=left,
        queue_history=queue_history,
    )


def run_many(make_controller, n=REPLICATIONS):
    return [run_simulation(make_controller(), seed=1000 + i) for i in range(n)]


def summarize(results):
    return {
        "Avg Wait (s)": np.mean([r.avg_wait for r in results]),
        "Wait Std": np.std([r.avg_wait for r in results]),
        "Max Queue (cars)": np.mean([r.max_queue for r in results]),
        "Throughput (cars/hr)": np.mean([r.throughput for r in results]),
        "Cars Left Waiting": np.mean([r.left_in_queue for r in results]),
    }


# ----------------------------------------------------------------------
# 4. OPTIMIZATION  (try many green times, keep the best)
# ----------------------------------------------------------------------
def optimize_fixed_green(candidates=range(10, 65, 5)):
    rows = []
    for g in candidates:
        res = run_many(lambda g=g: FixedController(g), n=10)
        rows.append((g, np.mean([r.avg_wait for r in res])))
    df = pd.DataFrame(rows, columns=["green_time", "avg_wait"])
    best = int(df.loc[df["avg_wait"].idxmin(), "green_time"])
    return best, df


# ----------------------------------------------------------------------
# 5. PLOTS
# ----------------------------------------------------------------------
def make_plots(all_results, sweep_df, best_green):
    os.makedirs(OUT_DIR, exist_ok=True)
    names = list(all_results.keys())
    colors = ["#d9534f", "#f0ad4e", "#5cb85c"]

    # Plot 1: queue length over time (average of all runs)
    plt.figure(figsize=(10, 4.5))
    for name, c in zip(names, colors):
        avg_q = np.mean([r.queue_history for r in all_results[name]], axis=0)
        plt.plot(avg_q, label=name, color=c, linewidth=1.5)
    plt.axvspan(RUSH_START, RUSH_END, color="grey", alpha=0.15, label="Rush hour")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Cars waiting (all roads)")
    plt.title("Queue Length Over Time")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/1_queue_over_time.png", dpi=150)
    plt.close()

    # Plot 2: bar comparison of average wait
    plt.figure(figsize=(6, 4.5))
    means = [np.mean([r.avg_wait for r in all_results[n]]) for n in names]
    stds = [np.std([r.avg_wait for r in all_results[n]]) for n in names]
    bars = plt.bar(names, means, yerr=stds, color=colors, capsize=5)
    for b, m in zip(bars, means):
        plt.text(b.get_x() + b.get_width() / 2, m + 1, f"{m:.1f}s", ha="center")
    plt.ylabel("Average waiting time per car (s)")
    plt.title("Controller Comparison")
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/2_wait_comparison.png", dpi=150)
    plt.close()

    # Plot 3: optimization curve
    plt.figure(figsize=(7, 4.5))
    plt.plot(sweep_df["green_time"], sweep_df["avg_wait"], "o-", color="#337ab7")
    plt.axvline(best_green, color="green", linestyle="--", label=f"Best = {best_green}s")
    plt.xlabel("Green time per phase (s)")
    plt.ylabel("Average waiting time (s)")
    plt.title("Optimization: Finding the Best Fixed Green Time")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/3_optimization_curve.png", dpi=150)
    plt.close()


# ----------------------------------------------------------------------
# 6. MAIN
# ----------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Smart Traffic Flow Simulation and Optimization")
    print("=" * 50)

    print("Step 1: Optimizing fixed green time ...")
    best_green, sweep_df = optimize_fixed_green()
    print(f"  Best fixed green time = {best_green} seconds\n")

    print(f"Step 2: Running {REPLICATIONS} simulations per controller ...")
    all_results = {
        "Fixed-Time": run_many(lambda: FixedController(30)),
        "Optimized Fixed": run_many(lambda: FixedController(best_green)),
        "Smart Adaptive": run_many(lambda: AdaptiveController()),
    }

    table = pd.DataFrame({k: summarize(v) for k, v in all_results.items()}).T.round(2)
    print("\nRESULTS (average of all runs)")
    print(table.to_string())

    base = table.loc["Fixed-Time", "Avg Wait (s)"]
    for name in ["Optimized Fixed", "Smart Adaptive"]:
        imp = (base - table.loc[name, "Avg Wait (s)"]) / base * 100
        print(f"\n{name}: waiting time reduced by {imp:.1f}% vs Fixed-Time (30 s)")

    table.to_csv(f"{OUT_DIR}/results.csv")
    sweep_df.to_csv(f"{OUT_DIR}/optimization_sweep.csv", index=False)
    make_plots(all_results, sweep_df, best_green)
    print(f"\nSaved tables and graphs in the '{OUT_DIR}' folder.")


if __name__ == "__main__":
    main()
