# Smart Traffic Flow Simulation and Optimization

**Course:** Solving Problems Through Modelling and Simulation
**Tool:** Python (NumPy, Pandas, Matplotlib)

---

## 1. Problem Statement
Traffic jams at intersections waste time and fuel. Most signals use a **fixed timer**, which does not care whether a road is full or empty. This project builds a computer simulation of a 4-way intersection to (a) measure how bad the waiting is, and (b) test whether a **smarter signal** and an **optimized timer** reduce it.

## 2. Objectives
1. Build a simulation of a 4-way intersection with random car arrivals.
2. Compare three signal strategies.
3. Find the best fixed green time using optimization.
4. Measure improvement in waiting time, queue length and throughput.

## 3. Type of Model
- **Discrete-time, stochastic simulation** (time moves in 1-second steps; arrivals are random).
- **Monte Carlo replication:** each strategy is run 20 times with different random seeds, and results are averaged, so one lucky or unlucky run does not mislead us.

## 4. System Description
| Item | Value |
|---|---|
| Roads | North, South, East, West (one lane each) |
| Phase 0 | North + South green |
| Phase 1 | East + West green |
| Arrivals | Random (Poisson process): N, S = 0.12 cars/s, E, W = 0.09 cars/s |
| Rush hour | Minute 20 to 40, arrivals x 1.5 |
| Service rate | 1 car leaves every 2 seconds on green |
| Yellow / lost time | 3 seconds at every change |
| Simulation length | 3600 s (1 hour) |

## 5. Assumptions
- Single lane per road, no turning, no pedestrians, no accidents.
- Every car takes the same time to cross.
- Car arrivals are independent and random.
- Drivers obey the signal.

## 6. Signal Strategies
1. **Fixed-Time:** 30 s green for each road pair. This is the "normal" traffic light (baseline).
2. **Optimized Fixed:** the program tries green times from 10 to 60 s and picks the one with the lowest average wait.
3. **Smart Adaptive:** looks at the queues every second.
   - Minimum green 10 s, maximum green 60 s.
   - Switch early if the green road is empty but cars are waiting on the red road.
   - Switch if the red road queue is more than 1.5 times the green road queue.

## 7. Algorithm (Flow)
```
for each second t in 0..3600:
    1. New cars arrive randomly on each road (join queue)
    2. If yellow is running -> count it down, then change phase
    3. Else ask controller: "switch now?"
         yes -> start yellow
         no  -> let cars on the green road leave (1 car / 2 s)
    4. Record total queue length
at the end: compute average wait, max queue, throughput
```

## 8. Performance Measures
- **Average waiting time** per car (main measure)
- **Maximum queue length**
- **Throughput** (cars that crossed in one hour)
- **Cars left waiting** at the end of the hour

## 9. Results (average of 20 runs)
| Controller | Avg Wait (s) | Max Queue | Throughput/hr | Left Waiting |
|---|---|---|---|---|
| Fixed-Time (30 s) | 16.51 | 24.3 | 1748.7 | 8.35 |
| Optimized Fixed (20 s) | 14.34 | 24.0 | 1749.2 | 7.90 |
| Smart Adaptive | **11.60** | **21.7** | 1753.3 | **3.75** |

- Optimization found the best fixed green time = **20 seconds**, which cut waiting by about **13%**.
- Smart Adaptive cut waiting by about **30%** compared with the normal fixed signal.

> Your numbers may differ slightly if you change the seeds or parameters. Always quote the numbers from your own final run.

Graphs are in the `traffic_output` folder:
- `1_queue_over_time.png` shows queue length through the hour, with the rush hour shaded.
- `2_wait_comparison.png` shows the average wait of the three controllers.
- `3_optimization_curve.png` shows wait against green time, with the best value marked.

## 10. Discussion
- During rush hour all controllers struggle, but the adaptive one recovers fastest because it moves green time to where the cars are.
- A very short fixed green wastes time in yellow changes. A very long one makes the other road wait too long. That is why the optimization curve is U-shaped.
- Throughput is almost the same for all (the road capacity is the limit), so the real gain is **less waiting**, not more cars.

## 11. Conclusion
A signal that reacts to the traffic works better than a fixed timer. Even a simple rule-based smart signal reduced average waiting by about 30%, and simply tuning the timer gave about 13%. This shows how simulation lets us test ideas safely before changing real roads.

## 12. Future Scope
- Multiple lanes and left/right turns
- A network of several connected intersections
- Reinforcement learning controller
- Real camera/sensor data
- Emergency vehicle priority
- Pedestrian crossing phases

## 13. How to Run
```
pip install numpy pandas matplotlib
python traffic_simulation.py
```

## 14. Possible Viva Questions
**Q1. Why simulation instead of testing on a real road?**
It is cheap, safe, repeatable and we can test many ideas quickly.

**Q2. Why Poisson arrivals?**
Cars on a road arrive randomly and independently, which a Poisson process describes well.

**Q3. Why run 20 replications?**
One run has randomness. Averaging many runs gives a stable, trustworthy result.

**Q4. What is optimization here?**
Searching for the green time value that gives the minimum average waiting time (grid search).

**Q5. Is this a discrete-event or continuous model?**
It is a discrete-time (time-stepped) stochastic model.

**Q6. What are the limitations?**
Single lane, no turns, constant service time, one intersection only.

**Q7. What does the adaptive controller do differently?**
It uses live queue lengths to extend or end green, instead of a fixed timer.
