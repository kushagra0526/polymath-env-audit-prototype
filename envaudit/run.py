import json
import random
from collections import Counter

from . import audit, env


def smoke_test(e, episodes=30):
    """Baseline: random-policy episodes. Flags 'trivial' if the start already passes, 'unsolvable' if nothing ever passes."""
    wins = 0
    for k in range(episodes):
        rng = random.Random(k)
        e.reset(seed=k)
        if e.verify(e.state):
            return ["trivial"]
        for _ in range(30):
            va = e.valid_actions()
            if not va:
                break
            _, ok, done = e.step(rng.choice(va))
            if ok:
                wins += 1
                break
    return [] if wins else ["unsolvable"]


def score(seeds, held, with_horizon=True):
    t, per = Counter(), {}
    defects = [None] * 3 + (env.HELD_DEFECTS if held else env.DEFECTS)
    for s in seeds:
        d = defects[s % len(defects)]
        e = env.Env(s, d if d != "horizon_short" else None, big=held)
        if d == "horizon_short":
            e.horizon = 3                                   # shorter than any solution
        found, base = audit.audit(e, with_horizon), smoke_test(env.Env(s, d if d != "horizon_short" else None, big=held))
        if d == "horizon_short":
            pass
        key = d or "clean"
        p = per.setdefault(key, Counter())
        p["n"] += 1
        p["audit_exact"] += (found == [d]) if d else (found == [])
        p["audit_contains"] += (d in found) if d else 0
        p["baseline_contains"] += (d in base) if d else 0
        p["flagged_other"] += len([f for f in found if f != d])
    return {k: dict(v) for k, v in sorted(per.items())}


def main():
    res = {"dev": score(range(0, 160), False), "held_out_run1": score(range(1000, 1160), True, with_horizon=False),
           "held_out_run2_with_horizon_check": score(range(1000, 1160), True, with_horizon=True)}
    json.dump(res, open("out/result.json", "w"), indent=1)
    for k, v in res.items():
        print(k)
        for d, c in v.items():
            print("  ", d, c)


if __name__ == "__main__":
    main()
