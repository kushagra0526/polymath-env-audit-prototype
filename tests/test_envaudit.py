from envaudit import audit, env


def test_clean_env_is_solvable_deterministic_and_passes_the_audit():
    e = env.Env(1)
    e.reset()
    assert audit.shortest_path(e) is not None and audit.check_deterministic(e)
    assert audit.audit(e) == []


def test_each_planted_defect_is_named():
    for d in ("nondeterministic", "unsolvable", "trivial", "leak", "loose_checker"):
        found = [audit.audit(env.Env(s, d)) for s in range(6)]
        assert all(d in f for f in found), (d, found)


def test_dead_end_is_found_only_after_the_irreversible_move():
    e = env.Env(3, "dead_end")
    e.reset()
    assert audit.shortest_path(e) is not None          # solvable at the start
    assert "dead_end" in audit.audit(e)


def test_replay_changes_state_when_unseeded_randomness_is_used():
    assert not audit.check_deterministic(env.Env(2, "nondeterministic"))
