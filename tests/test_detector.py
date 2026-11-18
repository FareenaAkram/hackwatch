import ast

import pytest

from hackwatch import detector, hacks, mutators, pipeline
from hackwatch.problems import PROBLEMS
from hackwatch.subtle import SUBTLE

CFG = pipeline.Config(n_random=40, n_probe=20)


def visible_args(ctx):
    return [ast.literal_eval(a) for a, _ in ctx.visible]


@pytest.mark.parametrize("p", PROBLEMS, ids=lambda p: p.name)
def test_honest_code_has_no_static_flags(p):
    ctx = pipeline.make_ctx(p, CFG)
    for code in [p.ref, *p.alts, *SUBTLE.get(p.name, [])]:
        assert detector.static_flags(code, visible_args(ctx)) == []


@pytest.mark.parametrize("p", PROBLEMS, ids=lambda p: p.name)
def test_every_hack_kind_trips_a_static_check(p):
    ctx = pipeline.make_ctx(p, CFG)
    fallback = mutators.apply_site(p.ref, mutators.find_sites(p.ref)[0]) if mutators.find_sites(p.ref) else p.ref
    for kind, code in hacks.make_hacks(ctx, fallback):
        flags = detector.static_flags(code, visible_args(ctx))
        assert flags, f"{p.name}/{kind} not caught statically"


def test_flag_kinds_per_hack():
    p = next(x for x in PROBLEMS if x.name == "dedupe")
    ctx = pipeline.make_ctx(p, CFG)
    got = {k: {f.kind for f in detector.static_flags(c, visible_args(ctx))} for k, c in hacks.make_hacks(ctx, p.ref)}
    assert "literal_case_matching" in got["lookup_table"]
    assert "literal_case_matching" in got["overfit_fallback"]
    assert {"literal_case_matching", "test_awareness"} <= got["test_awareness"]
    assert "always_equal" in got["always_equal"]
    assert "harness_escape" in got["exit_early"]


def test_literals_passed_to_calls_do_not_count():
    code = "def solve(s):\n    return s.replace('()', '').replace('[]', '') == ''\n"
    assert detector.static_flags(code, [("()",), ("[]",), ("(]",)]) == []


def test_dynamic_flags_type_anomaly_and_constant_output():
    probe = {"present": True, "results": [["None", "NoneType", ""]] * 10}
    flags = detector.dynamic_flags(probe, [(0, 1), (1, 2), None, (2, 3)])
    assert {f.kind for f in flags} == {"constant_output"} or {"type_anomaly"} <= {f.kind for f in flags}


def test_dynamic_early_exit_flag():
    flags = detector.dynamic_flags({"present": False, "rc": 0, "timeout": False, "results": []}, [1])
    assert [f.kind for f in flags] == ["harness_escape"]
    assert detector.dynamic_flags({"present": False, "rc": 1, "timeout": False, "results": []}, [1]) == []
