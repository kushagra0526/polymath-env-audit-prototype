# envaudit: is this training environment actually a good task?

Polymath builds "simulation environments to train & evaluate long-horizon AI agents" (https://polymathlabs.ai/). An environment with a programmatic verifier can be wrong in ways an agent's score hides: it cannot be solved, it is already solved at reset, it behaves differently on replay, its observation tells the agent the answer, its checker accepts wrong end states, or one early irreversible move makes it unsolvable (a dead end), which matters most for long horizons. This prototype audits an environment through a small black-box API and names the defect.

## What it does
`envaudit/env.py`: a crafting-task family (items A to D, rules that consume and produce items, a goal inventory, a step horizon, a verifier) with planted defects: `nondeterministic` (unseeded randomness in a rule), `unsolvable` (goal needs an item no rule makes), `trivial` (goal already met at reset), `leak` (the observation names the best next move), `dead_end` (a once-only resource that a careless action destroys), `loose_checker` (verifier ignores one requirement), and in held-out `horizon_short` (the horizon is shorter than any solution).
`envaudit/audit.py` uses only `reset / step / get_state / set_state / valid_actions / observe / verify`:
- **determinism:** replay random action sequences from the same seed and compare states;
- **solvability and horizon:** breadth-first search to the goal; no path = unsolvable; path longer than the horizon = `horizon_short`;
- **trivial:** the verifier passes at reset;
- **leak:** the observation contains a valid action while a solution exists;
- **dead ends:** random walks, then search again from every visited state; a state that is reachable, not solved and cannot reach the goal;
- **checker strictness:** take a solved state and lower each required item by one; a strict verifier must reject.
Baseline: 30 random-policy episodes (flags `trivial` when the start passes, `unsolvable` when nothing ever passes).

## Results (generated environments, a defect or none, known labels)
Dev: 160 environments (3 items). Held-out: 160 larger environments (4 items) with the new defect, fixed in git before the first run.

| defect (held-out) | n | audit names it | random-policy smoke test |
|---|---|---|---|
| nondeterministic | 16 | 16 | 0 |
| unsolvable | 16 | 16 | 16 |
| trivial | 16 | 16 | 16 |
| leak | 16 | 16 | 0 |
| loose_checker | 16 | 16 | 0 |
| dead_end | 16 | 14 (2 reported under another name) | 0 |
| horizon_short | 16 | 0 without the horizon check, 15 with it | 0 |
| clean | 48 | 48 pass with no flag | - |

Dev: every defect named exactly (17-18 each), 54/54 clean passed. The smoke test finds only the two defects that a random policy can see; leaks, bad checkers, nondeterminism and dead ends pass it.
The horizon check was written before the run and is an option, so the `horizon_short` row is an ablation (run 1 without it, run 2 with it), not a fix after the fact.

## Read this before believing the table
Environments, defects and the auditor are mine, in a state space small enough for exhaustive search (a few thousand states). Real long-horizon environments have huge or continuous state, hidden state that cannot be snapshotted, tools with side effects, and graders that are models; solvability and dead ends would have to be estimated by sampling, not proved. The planted defects are the easy kind. Nothing here uses Polymath environments or systems.

## Run it (3 commands)
```
pip install pytest
python -m pytest -q tests
python -m envaudit.run
```
Standard library only. 4 tests.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Polymath.
