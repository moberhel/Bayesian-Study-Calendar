import numpy as np
from study_planner.model import STATES, PARENTS, ORDER, build_cpts


def test_every_cpt_row_sums_to_one():
    for var, table in build_cpts().items():
        assert np.allclose(table.sum(axis=-1), 1.0), var


def test_cpt_shapes_match_parents_and_states():
    cpts = build_cpts()
    for var in ORDER:
        expected = tuple(len(STATES[p]) for p in PARENTS[var]) + (len(STATES[var]),)
        assert cpts[var].shape == expected, var


def test_order_is_topological_and_acyclic():
    seen = set()
    for var in ORDER:
        assert all(p in seen for p in PARENTS[var]), f"{var} listed before its parents"
        seen.add(var)
    assert set(ORDER) == set(STATES)


def test_network_has_at_most_ten_variables():
    assert len(ORDER) <= 10


def test_more_action_never_lowers_grade_probability():
    """Physical sanity: for fixed mastery/days, P(Grade=High) is non-decreasing in study gain."""
    g = build_cpts()["Grade"]  # [Mastery, Action, DaysLeft, Grade]
    # Action order: Intense5h, Moderate3h, Light1h, Rest
    for m in range(3):
        for d in range(3):
            high = [g[m, a, d, 2] for a in range(4)]
            assert high[0] >= high[1] >= high[2] >= high[3]
