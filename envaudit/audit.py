"""Black-box audit of a task environment: determinism, solvability, triviality, dead ends, observation leaks, checker strictness."""
import random
from collections import deque


def _hash(env):
    return env.get_state()


def shortest_path(env, from_state=None, limit=60000):
    """BFS over (state, once-flags) using only step/get_state/set_state. Returns the list of actions or None."""
    start = from_state if from_state is not None else env.get_state()
    env.set_state(start)
    key = lambda s: (s[0], s[1])
    seen = {key(start): None}
    q = deque([(start, [])])
    while q and len(seen) < limit:
        s, path = q.popleft()
        env.set_state(s)
        if env.verify(env.state) and path:
            env.set_state(start)
            return path
        for a in env.valid_actions():
            env.set_state(s)
            env.step(a, want_obs=False)
            ns = env.get_state()
            if key(ns) not in seen:
                seen[key(ns)] = 1
                q.append((ns, path + [a]))
    env.set_state(start)
    return None


def check_deterministic(env, trials=12, length=10):
    for k in range(trials):
        rng = random.Random(k)
        env.reset(seed=k)
        acts = []
        for _ in range(length):
            va = env.valid_actions()
            if not va:
                break
            acts.append(rng.choice(va))
            env.step(acts[-1], want_obs=False)
        h1 = env.get_state()
        env.reset(seed=k)
        for a in acts:
            if a in env.valid_actions():
                env.step(a, want_obs=False)
        if env.get_state() != h1:
            return False
    return True


def audit(env, with_horizon_check=True):
    out = []
    env.reset()
    if not check_deterministic(env):
        out.append("nondeterministic")
    env.reset()
    if env.verify(env.state):
        out.append("trivial")
    env.reset()
    sp = shortest_path(env)
    if sp is None:
        out.append("unsolvable")
    elif with_horizon_check and len(sp) > env.horizon:
        out.append("horizon_short")
    # observation leak: does the observation name a valid action on a shortest path?
    env.reset()
    obs = env.observe()
    if any(a in obs for a in env.rules) and sp:
        out.append("leak")
    # dead ends: random walks, then ask whether the goal is still reachable from every visited state
    env.reset()
    dead, memo = False, {}
    for k in range(6):
        rng = random.Random(100 + k)
        env.reset(seed=k)
        for _ in range(8):
            va = env.valid_actions()
            if not va:
                break
            env.step(rng.choice(va), want_obs=False)
            st = env.get_state()
            kk = (st[0], st[1])
            if kk not in memo:
                memo[kk] = shortest_path(env, st, limit=1500) is None
            env.set_state(st)
            if memo[kk] and sp is not None and not env.verify(env.state):
                dead = True
                break
        if dead:
            break
    if dead and "unsolvable" not in out:
        out.append("dead_end")
    # checker strictness: perturb a solved state in each field; a strict checker rejects at least the goal fields
    if sp:
        env.reset()
        for a in sp:
            env.step(a, want_obs=False)
        solved = dict(env.state)
        for item, need in env.goal.items():
            if need > 0:
                t = dict(solved)
                t[item] = need - 1
                if env.verify(t):
                    out.append("loose_checker")
                    break
    return sorted(set(out))
