import json
import threading

from hackwatch import pipeline, report
from hackwatch.cli import main

from .test_providers import CODE, Handler  # noqa: F401  (mock LLM server handler)


def small_build(tmp_path, **kw):
    cfg = pipeline.Config(n_random=40, n_probe=15, only=["dedupe", "pascal_row"], **kw)
    return cfg, *pipeline.build(cfg, log=lambda _: None)


def test_end_to_end_build_verify_and_outputs(tmp_path):
    cfg, cands, pairs, mstats = small_build(tmp_path)
    labels = {c["label"] for c in cands}
    assert {"correct", "subtle_bug", "hack"} <= labels
    hacks_ = [c for c in cands if c["label"] == "hack"]
    assert len(hacks_) == 10 and all(c["naive_pass"] and not c["strict_pass"] for c in hacks_)
    assert all(c["flagged"] for c in hacks_)
    assert not any(c["flagged"] for c in cands if c["label"] in ("correct", "subtle_bug"))
    assert pairs and all(p["critique"] for p in pairs)

    stats = report.build_stats(cfg, cands, pairs, mstats)
    assert stats["headline"]["hacks_naive_rewarded"] == stats["headline"]["hacks"]
    assert stats["pairs"]["naive"]["tie"] > 0  # naive reward cannot separate correct from hack
    assert stats["pairs"]["combined"]["wrong"] == 0
    report.write_outputs(cands, pairs, stats, tmp_path / "ds", tmp_path / "site")
    assert (tmp_path / "site" / "data.js").read_text().startswith("window.HACKWATCH = ")
    assert "Dataset card" in (tmp_path / "ds" / "DATASET_CARD.md").read_text()
    assert main(["verify", str(tmp_path / "ds")]) == 0


def test_verify_detects_tampering(tmp_path):
    cfg, cands, pairs, mstats = small_build(tmp_path)
    stats = report.build_stats(cfg, cands, pairs, mstats)
    report.write_outputs(cands, pairs, stats, tmp_path / "ds", tmp_path / "site")
    path = tmp_path / "ds" / "candidates.jsonl"
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    victim = next(r for r in rows if r["label"] == "hack" and r["kind"] == "lookup_table")
    victim["code"] = "def solve(*a):\n    return []\n"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert main(["verify", str(tmp_path / "ds")]) == 1


def test_llm_candidates_flow_through_the_same_graders(tmp_path):
    from http.server import HTTPServer

    from hackwatch.providers import AnthropicProvider

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        prov = AnthropicProvider("mock", api_key="k", base_url=f"http://127.0.0.1:{srv.server_port}")
        cfg = pipeline.Config(n_random=40, n_probe=15, only=["dedupe"], llm_samples=1)
        cands, pairs, mstats = pipeline.build(cfg, prov, log=lambda _: None)
    finally:
        srv.shutdown()
    llm = [c for c in cands if c["origin"] == "llm"]
    assert len(llm) == 2 and all(c["label"] == "correct" for c in llm)  # mock returns a correct solution
    stats = report.build_stats(cfg, cands, pairs, mstats)
    assert stats["llm"]["n"] == 2
    assert all(p["chosen"].split(":")[1] != "llm" for p in pairs)  # pairs use ground-truth-labelled candidates only
