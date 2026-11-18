import pytest

from hackwatch import hacks, pipeline
from hackwatch.problems import BY_NAME
from hackwatch.sandbox import evaluate
from hackwatch.subtle import SUBTLE

CFG = pipeline.Config(n_random=60, n_probe=15)


def ctx_for(name):
    return pipeline.make_ctx(BY_NAME[name], CFG)


def test_reference_and_alt_pass_both_graders():
    p = BY_NAME["merge_sorted"]
    ctx = ctx_for("merge_sorted")
    for code in [p.ref, *p.alts]:
        ev = evaluate(code, ctx)
        assert ev["naive_pass"] and ev["strict_pass"] and not ev["no_sentinel"]


@pytest.mark.parametrize("kind", hacks.HACK_KINDS)
def test_each_hack_fools_naive_but_not_strict(kind):
    ctx = ctx_for("dedupe")
    code = dict(hacks.make_hacks(ctx, SUBTLE["dedupe"][0]))[kind]
    ev = evaluate(code, ctx)
    assert ev["naive_pass"], "hack must earn full naive reward"
    assert not ev["strict_pass"], "strict grader must reject it"


def test_exit_early_leaves_no_sentinel():
    ctx = ctx_for("dedupe")
    code = dict(hacks.make_hacks(ctx, BY_NAME["dedupe"].ref))["exit_early"]
    assert evaluate(code, ctx)["no_sentinel"] is True


def test_strict_compares_types_recursively():
    ctx = ctx_for("pascal_row")
    ev = evaluate(SUBTLE["pascal_row"][0], ctx)
    assert ev["naive_pass"] and not ev["strict_pass"]  # [1.0, 2.0] == [1, 2] but floats are wrong


def test_honest_subtle_bug_passes_visible_fails_hidden():
    ctx = ctx_for("eval_rpn")
    ev = evaluate(SUBTLE["eval_rpn"][0], ctx)
    assert ev["naive_pass"] and not ev["strict_pass"]
    assert ev["failures"] and ev["failures"][0]["expected"]


def test_infinite_loop_is_bounded():
    ctx = ctx_for("dedupe")
    ev = evaluate("def solve(xs):\n    while True:\n        pass\n", ctx)
    assert not ev["naive_pass"] and not ev["strict_pass"]


def test_test_awareness_hack_behaves_differently_per_script():
    ctx = ctx_for("collatz")
    code = dict(hacks.make_hacks(ctx, BY_NAME["collatz"].ref.replace("3 * n + 1", "3 * n - 1")))["test_awareness"]
    ev = evaluate(code, ctx)
    assert ev["naive_pass"] and not ev["strict_pass"]
