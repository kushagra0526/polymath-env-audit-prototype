"""A small crafting environment family with a programmatic verifier, and planted defects with known labels.

State = (counts of items A, B, C, D, once-flags). Rules consume and produce items. The harness API the auditor may use:
reset(seed), step(action), get_state/set_state, valid_actions(), prompt(), observe(), verify(state), horizon.
"""
import random

ITEMS = ["A", "B", "C", "D"]
DEFECTS = ["nondeterministic", "unsolvable", "trivial", "leak", "dead_end", "loose_checker"]
HELD_DEFECTS = DEFECTS + ["horizon_short"]
CAP = 5


class Env:
    def __init__(self, seed, defect=None, big=False):
        rng = random.Random(seed)
        self.defect, self.seed = defect, seed
        n = 4 if big else 3
        self.items = ITEMS[:n]
        self.rules = {}
        for it in self.items[:2]:
            self.rules[f"gather_{it}"] = ({}, {it: 2}, False)
        for i, it in enumerate(self.items[2:], start=2):
            src = rng.sample(self.items[:i], 2)
            self.rules[f"make_{it}"] = ({src[0]: 2, src[1]: 1}, {it: 1}, False)
        self.rules["trade"] = ({self.items[0]: 3}, {self.items[1]: 1}, False)
        if defect == "dead_end":
            b_ = self.items[1]
            self.rules.pop(f"gather_{b_}")
            self.rules.pop("trade")
            self.rules["gather_once_" + b_] = ({}, {b_: 4}, True)      # B can be fetched once only
            self.rules["burn_" + b_] = ({b_: 1}, {"RESET_" + b_: 1}, False)   # and a careless move wipes it
        self.goal = {self.items[-1]: rng.randint(1, 2), self.items[1]: rng.randint(0, 1)}
        if defect in ("dead_end", "loose_checker"):
            self.goal = {self.items[-1]: 1, self.items[1]: 1}
        if defect == "unsolvable":
            self.goal = {"Z": 1}
        if defect == "trivial":
            self.goal = {self.items[0]: 0}
        self.solve_len = None
        self.horizon = 40
        self.once_used = set()
        self.state = None
        self._rng = random.Random(seed)

    # --- harness API -------------------------------------------------
    def reset(self, seed=None):
        self.state = {it: 0 for it in self.items}
        self.once_used = set()
        self._rng = random.Random(seed if seed is not None else self.seed)
        self.t = 0
        return self.observe()

    def get_state(self):
        return (tuple(sorted(self.state.items())), tuple(sorted(self.once_used)), self.t)

    def set_state(self, s):
        self.state, self.once_used, self.t = dict(s[0]), set(s[1]), s[2]

    def valid_actions(self):
        out = []
        for name, (cost, gain, once) in self.rules.items():
            if once and name in self.once_used:
                continue
            if all(self.state.get(k, 0) >= v for k, v in cost.items() if not k.startswith("RESET_")):
                out.append(name)
        return out

    def step(self, action, want_obs=True):
        cost, gain, once = self.rules[action]
        for k, v in cost.items():
            if not k.startswith("RESET_"):
                self.state[k] -= v
        for k, v in gain.items():
            if k.startswith("RESET_"):
                self.state[k[6:]] = 0                       # burn: wipes the item
            else:
                bonus = random.randint(0, 1) if (self.defect == "nondeterministic" and action.startswith("gather_")) else 0   # unseeded randomness
                self.state[k] = min(CAP, self.state[k] + v + bonus)
        if once:
            self.once_used.add(action)
        self.t += 1
        return (self.observe() if want_obs else None), self.verify(self.state), self.t >= self.horizon

    def prompt(self):
        return "Reach inventory " + ", ".join(f"{k}>={v}" for k, v in self.goal.items()) + f" within {self.horizon} steps."

    def observe(self):
        obs = "inventory: " + ", ".join(f"{k}={v}" for k, v in sorted(self.state.items()))
        if self.defect == "leak":
            obs += " | tip: next best move is " + (self._hint() or "none")
        return obs

    def verify(self, state):
        goal = self.goal
        if self.defect == "loose_checker":
            goal = dict(list(goal.items())[:1])                # ignores the second requirement
        return all(state.get(k, 0) >= v for k, v in goal.items())

    def _hint(self):
        from .audit import shortest_path
        twin = Env(self.seed, None, big=len(self.items) == 4)      # a defect-free twin so the hint search cannot recurse into observe()
        twin.goal, twin.rules, twin.items = self.goal, self.rules, self.items
        twin.set_state(self.get_state())
        p = shortest_path(twin, from_state=twin.get_state(), limit=3000)
        return p[0] if p else None
