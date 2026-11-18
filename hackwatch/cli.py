"""CLI: `python -m hackwatch build | verify | detect`."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import pipeline, report
from .detector import analyze
from .problems import BY_NAME
from .sandbox import evaluate


def cmd_build(a) -> int:
    cfg = pipeline.Config(seed=a.seed, workers=a.workers, only=a.only or [], llm_samples=a.llm_samples,
                          per_kind=a.per_kind)
    provider = None
    if a.provider:
        from .providers import make_provider
        provider = make_provider(a.provider, a.model, a.base_url)
    t0 = time.time()
    print(f"hackwatch: building (seed={cfg.seed}, workers={cfg.workers})")
    cands, pairs, mstats = pipeline.build(cfg, provider)
    stats = report.build_stats(cfg, cands, pairs, mstats)
    report.write_outputs(cands, pairs, stats, Path(a.out), Path(a.site))
    h = stats["headline"]
    print(f"done in {time.time() - t0:.0f}s: {len(cands)} candidates, {len(pairs)} pairs")
    print(f"naive reward accepted {h['hacks_naive_rewarded']}/{h['hacks']} hacks; "
          f"detector flagged {h['hacks_flagged']}/{h['hacks']}; "
          f"false positives on correct: {h['correct_wrongly_flagged']}/{h['correct_total']}")
    return 0


def cmd_verify(a) -> int:
    d = Path(a.dataset)
    stats = json.loads((d / "stats.json").read_text())
    cfg = pipeline.Config(**stats["meta"]["config"])
    cands = [json.loads(x) for x in (d / "candidates.jsonl").read_text().splitlines() if x]
    ctxs = {}
    for c in cands:
        if c["problem"] not in ctxs:
            ctxs[c["problem"]] = pipeline.make_ctx(BY_NAME[c["problem"]], cfg)
    results = pipeline.pmap(lambda c: pipeline.grade(c["code"], ctxs[c["problem"]], c["origin"]), cands, a.workers)
    bad = 0
    for c, g in zip(cands, results):
        diff = [k for k in ("naive_pass", "strict_score", "flagged", "label") if g[k] != c[k]]
        if diff:
            bad += 1
            print(f"MISMATCH {c['id']}: {', '.join(diff)}")
    print(f"{len(cands) - bad}/{len(cands)} candidates re-graded identically from candidates.jsonl")
    return 1 if bad else 0


def cmd_detect(a) -> int:
    cfg = pipeline.Config()
    ctx = pipeline.make_ctx(BY_NAME[a.problem], cfg)
    code = Path(a.file).read_text(encoding="utf-8")
    ev = evaluate(code, ctx, probe=True)
    flags = analyze(code, ctx, ev["probe"])
    print(f"problem: {a.problem}")
    print(f"naive reward (visible examples): {'FULL' if ev['naive_pass'] else 'none'}")
    print(f"strict score (hidden cases):     {ev['strict_score']:.0%}")
    if flags:
        print("detector: HACK SUSPECTED")
        for f in flags:
            where = f" (lines {', '.join(map(str, f.lines))})" if f.lines else ""
            print(f"  - {f.kind}: {f.detail}{where}")
    else:
        print("detector: no hack indicators")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hackwatch", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="generate candidates, grade, detect, write dataset")
    b.add_argument("--out", default="dataset")
    b.add_argument("--site", default="site")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--workers", type=int, default=2)
    b.add_argument("--per-kind", type=int, default=3)
    b.add_argument("--only", nargs="*", help="restrict to these problem names")
    b.add_argument("--provider", choices=["anthropic", "openai"], help="also sample candidates from a real LLM")
    b.add_argument("--model", help="model name for --provider")
    b.add_argument("--base-url")
    b.add_argument("--llm-samples", type=int, default=0, help="samples per prompt style per problem")
    b.set_defaults(func=cmd_build)
    v = sub.add_parser("verify", help="re-grade every stored candidate and compare")
    v.add_argument("dataset", nargs="?", default="dataset")
    v.add_argument("--workers", type=int, default=2)
    v.set_defaults(func=cmd_verify)
    dd = sub.add_parser("detect", help="grade and scan one solution file")
    dd.add_argument("file")
    dd.add_argument("--problem", required=True, choices=sorted(BY_NAME))
    dd.set_defaults(func=cmd_detect)
    args = ap.parse_args(argv)
    if args.cmd == "build" and args.provider and not args.model:
        ap.error("--provider requires --model")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
